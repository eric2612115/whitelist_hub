"""Base crew implementation for Whitelist Hub analysis."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from crewai import Crew, Agent, Task, Process

logger = logging.getLogger(__name__)


class BaseCrew:
    """Base crew implementation for project analysis."""
    
    def __init__(
        self,
        ai_client: Any,
        prompt_manager: Any,
        process: Process = Process.sequential,
        verbose: bool = True,
        **kwargs
    ):
        """Initialize the crew.
        
        Args:
            ai_client: AI client for crew agents
            prompt_manager: Prompt manager for crew agents
            process: CrewAI process type (sequential, hierarchical)
            verbose: Whether to enable verbose logging
            **kwargs: Additional arguments for crew setup
        """
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager
        self.process = process
        self.verbose = verbose
        self.crew_args = kwargs
        
        # Initialize empty crew elements
        self.agents = {}
        self.tasks = []
        self._crew = None
        self.results = {}
        
        # Logging 
        self.execution_start_time = None
        self.execution_end_time = None
        self.logs = []
    
    def add_agent(self, agent_id: str, agent: Agent):
        """Add an agent to the crew.
        
        Args:
            agent_id: Unique identifier for the agent
            agent: CrewAI agent instance
        """
        self.agents[agent_id] = agent
        return self
    
    def add_task(self, task: Task):
        """Add a task to the crew.
        
        Args:
            task: CrewAI task instance
        """
        self.tasks.append(task)
        return self
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent instance if exists, None otherwise
        """
        return self.agents.get(agent_id)
    
    def build_crew(self) -> Crew:
        """Build the CrewAI crew instance.
        
        Returns:
            CrewAI Crew instance
        """
        if not self.agents:
            raise ValueError("No agents added to crew")
        
        if not self.tasks:
            raise ValueError("No tasks added to crew")
        
        self._crew = Crew(
            agents=list(self.agents.values()),
            tasks=self.tasks,
            process=self.process,
            verbose=self.verbose,
            **self.crew_args
        )
        
        return self._crew
    
    async def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the crew's tasks.
        
        Args:
            context: Optional context data for crew
            
        Returns:
            Results from crew execution
        """
        self.execution_start_time = datetime.now()
        
        if self._crew is None:
            self.build_crew()
        
        try:
            # Set shared context for the crew if provided
            if context and hasattr(self._crew, "set_context"):
                for key, value in context.items():
                    self._crew.set_context(key, value)
            
            # Run the crew
            result = self._crew.kickoff()
            
            # Store results
            self.results = result
            
            # Log completion
            self._log_event("crew_completed", {
                "status": "success",
                "result_length": len(str(result)) if isinstance(result, str) else "non-string result"
            })
            
            return result
            
        except Exception as e:
            logger.exception(f"Error running crew: {e}")
            self._log_event("crew_error", {
                "error": str(e)
            })
            raise
            
        finally:
            self.execution_end_time = datetime.now()
    
    def _log_event(self, event_type: str, data: Dict[str, Any] = None):
        """Log an event during crew execution.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data or {}
        })
        
        if self.verbose:
            logger.info(f"Crew event: {event_type} - {data}")
    
    def get_execution_time(self) -> Optional[float]:
        """Get execution time in seconds.
        
        Returns:
            Execution time if execution is completed, None otherwise
        """
        if self.execution_start_time and self.execution_end_time:
            return (self.execution_end_time - self.execution_start_time).total_seconds()
        return None
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get execution logs.
        
        Returns:
            List of log entries
        """
        return self.logs
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary.
        
        Returns:
            Summary of crew execution
        """
        return {
            "start_time": self.execution_start_time.isoformat() if self.execution_start_time else None,
            "end_time": self.execution_end_time.isoformat() if self.execution_end_time else None,
            "execution_time_seconds": self.get_execution_time(),
            "agents_count": len(self.agents),
            "tasks_count": len(self.tasks),
            "process_type": str(self.process),
            "status": "completed" if self.execution_end_time else "running",
            "has_results": bool(self.results)
        }
