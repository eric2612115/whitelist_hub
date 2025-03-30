"""Base agent implementation with Re-Act framework."""

import asyncio
import logging
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Union

from ..models.analysis_log import AnalysisLog, AnalysisStep, AgentChallenge, AgentPerformanceMetrics
from ..prompts.prompt_manager import PromptManager
from ..utils.ai_client import AIClient

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseAgent:
    """Base class for all agents in the system."""
    
    def __init__(
        self,
        agent_type: str,
        ai_client: AIClient,
        prompt_manager: PromptManager,
        max_iterations: int = 10,
    ):
        """Initialize agent.
        
        Args:
            agent_type: Type of agent (coordinator, crawler, analyzer, verifier)
            ai_client: Client for AI model API
            prompt_manager: Manager for prompt templates
            max_iterations: Maximum iterations to prevent infinite loops
        """
        self.agent_type = agent_type
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager
        self.max_iterations = max_iterations
        
        # Logging and state tracking
        self.log = []
        self.challenges = []
        self.iteration_count = 0
        self.execution_start_time = None
        self.execution_end_time = None
        self.total_tokens_used = 0
        self.prompt_versions_used = set()
        self.response_times = []
        
        # Fallback strategies
        self.fallback_strategies = {
            "timeout": self._handle_timeout,
            "error": self._handle_error,
            "unclear_response": self._handle_unclear_response,
        }
    
    async def run(self, task: str, context: Dict[str, Any], initial_state: str) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Run the agent with Re-Act loop.
        
        Args:
            task: Task description
            context: Context information
            initial_state: Initial state for the agent
        
        Returns:
            Tuple of (results, analysis log)
        """
        self.execution_start_time = time.time()
        self.state = initial_state
        self.context = context
        self.task = task
        
        try:
            while self.state != "completed" and self.iteration_count < self.max_iterations:
                try:
                    # Generate state-specific prompt
                    prompt, prompt_version = self._generate_prompt()
                    self.prompt_versions_used.add(prompt_version)
                    
                    # Get AI response
                    start_time = time.time()
                    ai_response = await self.ai_client.get_completion(prompt)
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    self.response_times.append(response_time)
                    
                    # Update token usage
                    self.total_tokens_used += ai_response.get("usage", {}).get("total_tokens", 0)
                    
                    # Process response
                    observation, reasoning, action, next_state = self._process_response(ai_response)
                    
                    # Log the step
                    self._log_step(observation, reasoning, action, response_time)
                    
                    # Execute action
                    result = await self._execute_action(action)
                    
                    # Update context with result
                    self.context.update(result)
                    
                    # Update state
                    self.state = next_state
                    self.iteration_count += 1
                    
                except Exception as e:
                    # Error handling and recovery
                    error_type = self._classify_error(e)
                    self.fallback_strategies[error_type](e)
                    
                    # Log the error
                    self._log_error(e, error_type)
                    
                    # Decide whether to continue
                    if not self._should_continue_after_error(error_type, e):
                        break
        
        finally:
            # Always create summary even if we exit with error
            self.execution_end_time = time.time()
            result_summary = self._create_summary()
            self.log.append({"summary": result_summary})
        
        # Create analysis log
        analysis_log = self._create_analysis_log()
        
        return self.context, analysis_log
    
    def _generate_prompt(self) -> Tuple[str, str]:
        """Generate prompt for current state.
        
        Returns:
            Tuple of (prompt, prompt_version)
        """
        try:
            prompt, version = self.prompt_manager.get_prompt(
                state=self.state,
                agent_type=self.agent_type,
                context=self.context,
                task=self.task,
                previous_responses=[step.get("reasoning", "") for step in self.log],
                simplify=self.context.get("simplify_next_prompt", False)
            )
            return prompt, version
        except Exception as e:
            logger.error(f"Error generating prompt: {e}")
            # Fallback to basic prompt
            return (
                f"You are the {self.agent_type.capitalize()} Agent. "
                f"Your task is: {self.task}. "
                f"Current state: {self.state}. "
                f"Please analyze the information and provide your reasoning, then determine the next action.",
                "fallback_v1"
            )
    
    def _process_response(self, response: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any], str]:
        """Process AI response to extract observation, reasoning, action and next state.
        
        Args:
            response: AI response
        
        Returns:
            Tuple of (observation, reasoning, action, next_state)
        """
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        try:
            # Try to extract structured information
            sections = content.split("## ")
            
            observation = ""
            reasoning = ""
            action = {}
            next_state = "completed"  # Default to completed if not specified
            
            for section in sections:
                if section.startswith("Observation"):
                    observation = section.replace("Observation:", "").strip()
                elif section.startswith("Reasoning"):
                    reasoning = section.replace("Reasoning:", "").strip()
                elif section.startswith("Action"):
                    action_text = section.replace("Action:", "").strip()
                    # Parse action into dictionary
                    action_lines = action_text.split("\n")
                    action_type = action_lines[0].strip() if action_lines else ""
                    action_params = {}
                    
                    for line in action_lines[1:]:
                        if ":" in line:
                            key, value = line.split(":", 1)
                            action_params[key.strip()] = value.strip()
                    
                    action = {
                        "type": action_type,
                        "params": action_params
                    }
                elif section.startswith("Next State"):
                    next_state = section.replace("Next State:", "").strip()
            
            # If we couldn't parse structured format, use content as reasoning
            if not reasoning:
                reasoning = content
                observation = "Processed AI response"
                action = {"type": "default", "params": {}}
            
            return observation, reasoning, action, next_state
            
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            # Return defaults if parsing fails
            return (
                "Failed to parse AI response",
                content,
                {"type": "default", "params": {}},
                "error_recovery"
            )
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action based on type.
        
        Args:
            action: Action to execute
        
        Returns:
            Result of action execution
        """
        action_type = action.get("type", "").lower()
        params = action.get("params", {})
        
        # Base implementation - should be overridden by subclasses
        if action_type == "collect_data":
            return {"data_collected": True, "message": "Data collection simulated"}
        elif action_type == "analyze":
            return {"analysis_complete": True, "message": "Analysis simulated"}
        elif action_type == "verify":
            return {"verification_complete": True, "message": "Verification simulated"}
        elif action_type == "complete":
            return {"task_complete": True, "message": "Task completed"}
        else:
            return {"action_unknown": True, "message": f"Unknown action type: {action_type}"}
    
    def _log_step(self, observation: str, reasoning: str, action: Dict[str, Any], execution_time_ms: float):
        """Log a step in the agent's process.
        
        Args:
            observation: Observation from the environment
            reasoning: Agent's reasoning process
            action: Action taken by the agent
            execution_time_ms: Execution time in milliseconds
        """
        self.log.append({
            "step": self.iteration_count + 1,
            "state": self.state,
            "observation": observation,
            "reasoning": reasoning,
            "action": action,
            "confidence": self._calculate_step_confidence(),
            "execution_time_ms": execution_time_ms
        })
    
    def _log_error(self, error: Exception, error_type: str):
        """Log an error.
        
        Args:
            error: Exception that occurred
            error_type: Type of error
        """
        self.challenges.append({
            "type": error_type,
            "description": str(error),
            "traceback": traceback.format_exc(),
            "state": self.state,
            "step": self.iteration_count + 1
        })
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error into predefined types.
        
        Args:
            error: Exception to classify
        
        Returns:
            Error type
        """
        if isinstance(error, asyncio.TimeoutError):
            return "timeout"
        elif isinstance(error, (ValueError, TypeError, KeyError, IndexError)):
            return "error"
        else:
            return "unclear_response"
    
    def _handle_timeout(self, error: Exception):
        """Handle timeout errors.
        
        Args:
            error: Exception that occurred
        """
        # Simplify prompt and retry
        self.context["simplify_next_prompt"] = True
        logger.warning(f"Timeout error: {error}. Simplifying next prompt.")
    
    def _handle_error(self, error: Exception):
        """Handle general errors.
        
        Args:
            error: Exception that occurred
        """
        # Set recovery strategy based on error type
        logger.error(f"Error in agent execution: {error}")
        self.state = "error_recovery"
    
    def _handle_unclear_response(self, error: Exception):
        """Handle unclear model responses.
        
        Args:
            error: Exception that occurred
        """
        # Reformulate prompt to get clearer response
        logger.warning(f"Unclear response: {error}. Reformulating prompt.")
        self.context["simplify_next_prompt"] = True
        self.context["clarify_instructions"] = True
    
    def _should_continue_after_error(self, error_type: str, error: Exception) -> bool:
        """Decide whether to continue after an error.
        
        Args:
            error_type: Type of error
            error: Exception that occurred
        
        Returns:
            Whether to continue
        """
        # Decision based on error type and severity
        if error_type == "timeout" and self.iteration_count < self.max_iterations - 1:
            return True
        if error_type == "unclear_response" and self.iteration_count < self.max_iterations - 1:
            return True
        if error_type == "error" and not isinstance(error, (SystemError, MemoryError, ImportError)):
            return self.iteration_count < self.max_iterations - 1
        return False
    
    def _calculate_step_confidence(self) -> float:
        """Calculate confidence for the current step.
        
        Returns:
            Confidence score (0-1)
        """
        # Simple implementation - can be overridden by subclasses
        base_confidence = 0.7
        
        # Reduce confidence if we've had errors
        confidence = base_confidence - (len(self.challenges) * 0.1)
        
        # Reduce confidence if we're simplifying prompts
        if self.context.get("simplify_next_prompt", False):
            confidence -= 0.1
        
        return max(0.1, min(confidence, 1.0))
    
    def _create_summary(self) -> Dict[str, Any]:
        """Create a summary of the analysis process.
        
        Returns:
            Summary dictionary
        """
        # Summarize completed analysis steps and results
        return {
            "completed_steps": self.iteration_count,
            "final_state": self.state,
            "key_observations": [log.get("observation") for log in self.log if "observation" in log],
            "confidence_level": self._calculate_overall_confidence(),
            "execution_time_ms": int((self.execution_end_time - self.execution_start_time) * 1000),
            "challenges_encountered": len(self.challenges),
            "total_tokens_used": self.total_tokens_used
        }
    
    def _calculate_overall_confidence(self) -> float:
        """Calculate overall confidence in the results.
        
        Returns:
            Confidence score (0-1)
        """
        # Calculate confidence score based on step success and consistency
        if not self.log:
            return 0.0
        
        # Base confidence on current progress
        base_confidence = min(0.5 + (0.5 * (self.iteration_count / self.max_iterations)), 0.95)
        
        # Adjust based on challenges
        challenge_penalty = min(len(self.challenges) * 0.1, 0.5)
        
        # Average step confidence
        step_confidences = [step.get("confidence", 0) for step in self.log if "confidence" in step]
        avg_step_confidence = sum(step_confidences) / len(step_confidences) if step_confidences else 0.5
        
        # Combine factors
        overall_confidence = (base_confidence * 0.4) + (avg_step_confidence * 0.6) - challenge_penalty
        
        return max(0.1, min(overall_confidence, 1.0))
    
    def _create_analysis_log(self) -> AnalysisLog:
        """Create analysis log from agent execution.
        
        Returns:
            Analysis log
        """
        # Convert log to AnalysisStep objects
        analysis_steps = []
        for log_entry in self.log:
            if "summary" in log_entry:
                continue
            
            analysis_steps.append(AnalysisStep(
                step=log_entry.get("step", 0),
                state=log_entry.get("state", ""),
                observation=log_entry.get("observation", ""),
                reasoning=log_entry.get("reasoning", ""),
                action=log_entry.get("action", {}),
                result=log_entry.get("result"),
                confidence=log_entry.get("confidence", 0.5),
                execution_time_ms=log_entry.get("execution_time_ms", 0)
            ))
        
        # Convert challenges to AgentChallenge objects
        agent_challenges = []
        for challenge in self.challenges:
            agent_challenges.append(AgentChallenge(
                type=challenge.get("type", "unknown"),
                description=challenge.get("description", ""),
                resolution=challenge.get("resolution"),
                impact_on_analysis=challenge.get("impact")
            ))
        
        # Calculate performance metrics
        performance_metrics = AgentPerformanceMetrics(
            decisiveness=self._calculate_decisiveness(),
            thoroughness=self._calculate_thoroughness(),
            accuracy=None,  # Need external validation
            adaptation=self._calculate_adaptation()
        )
        
        # Create final log
        final_result = self.context.copy()
        
        # Ensure summarized result doesn't contain too much data
        if "original_data" in final_result:
            del final_result["original_data"]
        
        return AnalysisLog(
            project_id=self.context.get("project_id", ""),
            contract_id=self.context.get("contract_id", ""),
            analysis_id=f"{self.agent_type}-{datetime.now().isoformat()}",
            agent_type=self.agent_type,
            timestamp=datetime.now(),
            analysis_steps=analysis_steps,
            challenges=agent_challenges,
            prompt_statistics={
                "total_tokens": self.total_tokens_used,
                "prompt_versions_used": list(self.prompt_versions_used),
                "average_response_time_ms": sum(self.response_times) / len(self.response_times) if self.response_times else 0
            },
            final_result=final_result,
            execution_time_ms=int((self.execution_end_time - self.execution_start_time) * 1000),
            agent_performance_metrics=performance_metrics
        )
    
    def _calculate_decisiveness(self) -> float:
        """Calculate decisiveness metric.
        
        Returns:
            Decisiveness score (0-1)
        """
        if not self.log:
            return 0.5
        
        # Measure how directly the agent progressed to solution
        progress_efficiency = self.iteration_count / self.max_iterations
        
        # Less iterations is better if task was completed
        if self.state == "completed":
            decisiveness = 1.0 - (progress_efficiency * 0.5)
        else:
            decisiveness = progress_efficiency
        
        return max(0.1, min(decisiveness, 1.0))
    
    def _calculate_thoroughness(self) -> float:
        """Calculate thoroughness metric.
        
        Returns:
            Thoroughness score (0-1)
        """
        # Measure detail level in reasoning
        if not self.log:
            return 0.5
        
        # Average length of reasoning as a proxy for thoroughness
        avg_reasoning_length = sum(len(step.get("reasoning", "")) for step in self.log) / len(self.log)
        length_factor = min(avg_reasoning_length / 500, 1.0)
        
        # Consider number of observations made
        observation_count = sum(1 for step in self.log if step.get("observation"))
        observation_factor = min(observation_count / 5, 1.0)
        
        return (length_factor * 0.7) + (observation_factor * 0.3)
    
    def _calculate_adaptation(self) -> float:
        """Calculate adaptation metric.
        
        Returns:
            Adaptation score (0-1)
        """
        if not self.challenges:
            return 1.0
        
        # Measure how well agent recovered from challenges
        challenges_count = len(self.challenges)
        recovery_count = sum(1 for challenge in self.challenges if challenge.get("resolution"))
        
        if challenges_count == 0:
            return 1.0
        
        return recovery_count / challenges_count
