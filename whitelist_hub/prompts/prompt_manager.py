"""Prompt management system for AI agents."""

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import difflib
import json

from ..db.mongodb import get_collection
from .prompt_template import PromptTemplate, PromptTemplateMetadata

logger = logging.getLogger(__name__)


class PromptManager:
    """Manager for AI prompt templates with version control."""
    
    def __init__(self, use_db: bool = True, templates_dir: Optional[str] = None):
        """Initialize the prompt manager.
        
        Args:
            use_db: Whether to use database storage
            templates_dir: Directory for template files
        """
        self.use_db = use_db
        self.templates_dir = templates_dir
        self.current_versions = {}
        self._load_current_versions()
    
    async def _load_current_versions(self):
        """Load current version information for all templates."""
        if self.use_db:
            try:
                templates_metadata = await get_collection("prompt_metadata").find({}).to_list(None)
                for metadata in templates_metadata:
                    self.current_versions[metadata["name"]] = metadata["current_version"]
            except Exception as e:
                logger.error(f"Error loading template versions: {e}")
        elif self.templates_dir:
            # Load from filesystem
            try:
                for filename in os.listdir(self.templates_dir):
                    if filename.endswith(".txt"):
                        # Parse template name and version from filename
                        # Expected format: template_name.v1.txt
                        parts = filename.split(".")
                        if len(parts) >= 3 and parts[-2].startswith("v"):
                            name = parts[0]
                            version = int(parts[-2][1:])  # Extract number after 'v'
                            
                            # Update current version if higher
                            self.current_versions[name] = max(
                                self.current_versions.get(name, 0),
                                version
                            )
            except Exception as e:
                logger.error(f"Error loading template versions from filesystem: {e}")
    
    async def get_template(self, template_name: str, version: Optional[int] = None) -> Optional[PromptTemplate]:
        """Get a specific template version.
        
        Args:
            template_name: Name of the template
            version: Specific version to get (default: latest)
            
        Returns:
            Template if found, None otherwise
        """
        if version is None:
            version = self.current_versions.get(template_name, 1)
        
        if self.use_db:
            try:
                template_doc = await get_collection("prompt_templates").find_one(
                    {"name": template_name, "version": version}
                )
                if template_doc:
                    return PromptTemplate(**template_doc)
            except Exception as e:
                logger.error(f"Error fetching template from database: {e}")
        
        # Fallback to filesystem if DB fetch failed or use_db is False
        if self.templates_dir:
            template_path = os.path.join(self.templates_dir, f"{template_name}.v{version}.txt")
            if os.path.exists(template_path):
                try:
                    with open(template_path, "r") as f:
                        content = f.read()
                        return PromptTemplate(
                            name=template_name,
                            version=version,
                            content=content,
                            author="system",
                            created_at=datetime.fromtimestamp(os.path.getctime(template_path))
                        )
                except Exception as e:
                    logger.error(f"Error reading template file: {e}")
        
        return None
    
    async def get_prompt(
        self,
        state: str,
        agent_type: str,
        context: Dict,
        task: str,
        previous_responses: Optional[List[str]] = None,
        simplify: bool = False
    ) -> Tuple[str, str]:
        """Get appropriate prompt for current state and context.
        
        Args:
            state: Current state of the agent
            agent_type: Type of agent
            context: Context for prompt formatting
            task: Current task
            previous_responses: Previous agent responses
            simplify: Whether to simplify the prompt
            
        Returns:
            Tuple of (prompt, version)
        """
        template_name = f"{agent_type}_{state}"
        template = await self.get_template(template_name)
        
        if template is None:
            # Try fallback to agent type only
            template = await self.get_template(agent_type)
        
        if template is None:
            # Use default template with minimal formatting
            logger.warning(f"No template found for {template_name} or {agent_type}. Using default.")
            template_content = (
                "You are the {agent_type} Agent for the Whitelist Hub system.\n\n"
                "TASK:\n{task}\n\n"
                "CONTEXT:\n{context_str}\n\n"
                "Think step-by-step about how to complete this task.\n"
                "Provide your reasoning process, then your next action.\n\n"
                "## Observation\n\n"
                "## Reasoning\n\n"
                "## Action\n\n"
                "## Next State\n"
            )
            version = "default.v1"
        else:
            template_content = template.content
            version = f"{template.name}.v{template.version}"
        
        # Prepare context for formatting
        formatting_context = context.copy()
        formatting_context["agent_type"] = agent_type
        formatting_context["task"] = task
        
        # Convert complex objects to strings for formatting
        context_str = ""
        for key, value in formatting_context.items():
            if isinstance(value, (dict, list)):
                context_str += f"{key}:\n{json.dumps(value, indent=2)}\n\n"
            else:
                context_str += f"{key}: {value}\n"
        
        formatting_context["context_str"] = context_str
        
        # Format template with context
        try:
            enhanced_template = template_content.format(**formatting_context)
        except KeyError as e:
            logger.warning(f"Missing key in template formatting: {e}. Using basic substitution.")
            enhanced_template = template_content.replace("{agent_type}", agent_type)
            enhanced_template = enhanced_template.replace("{task}", task)
            enhanced_template = enhanced_template.replace("{context_str}", context_str)
        
        # Adjust based on previous responses if available
        if previous_responses and len(previous_responses) >= 2:
            if self._detect_repetition(previous_responses):
                enhanced_template += "\nPlease try a new approach, as previous responses seem to be repetitive."
            
            if self._detect_confusion(previous_responses):
                enhanced_template += "\nPlease be more explicit and structured in your analysis."
        
        # Simplify prompt if requested
        if simplify:
            enhanced_template = self._simplify_prompt(enhanced_template)
        
        return enhanced_template, version
    
    def _simplify_prompt(self, prompt: str) -> str:
        """Simplify prompt to reduce complexity.
        
        Args:
            prompt: Prompt to simplify
            
        Returns:
            Simplified prompt
        """
        # Remove examples and non-essential instructions
        lines = prompt.split('\n')
        simplified = []
        skip_example = False
        
        for line in lines:
            if line.strip().lower().startswith(("example", "for example")):
                skip_example = True
                continue
            
            if skip_example:
                if line.strip() == "" or line.startswith("#"):
                    skip_example = False
                else:
                    continue
            
            # Keep core instructions but skip verbose explanations
            if not (line.strip().startswith(("note:", "hint:", "remember:")) or "unnecessary details" in line.lower()):
                simplified.append(line)
        
        # Make sure we have all the required sections
        result = '\n'.join(simplified)
        
        required_sections = ["Observation", "Reasoning", "Action", "Next State"]
        missing_sections = []
        
        for section in required_sections:
            if f"## {section}" not in result:
                missing_sections.append(f"## {section}\n")
        
        if missing_sections:
            result += "\n" + "\n".join(missing_sections)
        
        return result
    
    def _detect_repetition(self, responses: List[str]) -> bool:
        """Detect repetitive patterns in responses.
        
        Args:
            responses: List of previous responses
            
        Returns:
            Whether repetition is detected
        """
        if len(responses) < 2:
            return False
        
        last = responses[-1]
        second_last = responses[-2]
        
        # Simple similarity calculation
        similarity = self._calculate_similarity(last, second_last)
        return similarity > 0.8  # 80% similarity threshold
    
    def _detect_confusion(self, responses: List[str]) -> bool:
        """Detect confusion or uncertainty in responses.
        
        Args:
            responses: List of previous responses
            
        Returns:
            Whether confusion is detected
        """
        if not responses:
            return False
        
        last_response = responses[-1].lower()
        uncertainty_markers = [
            "possibly", "perhaps", "uncertain", "difficult to determine", 
            "unclear", "not sure", "might be", "could be", "ambiguous"
        ]
        
        # Check for multiple questions in the response
        questions = last_response.count("?")
        
        # Check for uncertainty markers
        uncertainty_count = sum(1 for marker in uncertainty_markers if marker in last_response)
        
        return uncertainty_count >= 3 or questions >= 3
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        # Convert to sets of words
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def create_new_version(
        self, 
        template_name: str, 
        content: str, 
        author: str, 
        change_notes: str
    ) -> int:
        """Create a new version of a template.
        
        Args:
            template_name: Template name
            content: Template content
            author: Author of change
            change_notes: Notes about the change
            
        Returns:
            New version number
        """
        current_version = self.current_versions.get(template_name, 0)
        new_version = current_version + 1
        
        if self.use_db:
            try:
                # Store the new version
                template = PromptTemplate(
                    name=template_name,
                    version=new_version,
                    content=content,
                    author=author,
                    change_notes=change_notes,
                    created_at=datetime.now(),
                    effectiveness_metrics={
                        "avg_score": None,
                        "uses": 0,
                        "successes": 0,
                        "success_rate": None
                    }
                )
                
                await get_collection("prompt_templates").insert_one(template.dict(by_alias=True))
                
                # Update current version
                self.current_versions[template_name] = new_version
                await get_collection("prompt_metadata").update_one(
                    {"name": template_name},
                    {"$set": {"current_version": new_version}},
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Error creating new template version in database: {e}")
                return current_version
        
        # Store in filesystem as well if directory provided
        if self.templates_dir:
            try:
                template_path = os.path.join(self.templates_dir, f"{template_name}.v{new_version}.txt")
                with open(template_path, "w") as f:
                    f.write(content)
                
                # Store metadata
                metadata_path = os.path.join(self.templates_dir, f"{template_name}.metadata.json")
                metadata = {
                    "name": template_name,
                    "current_version": new_version,
                    "versions": [
                        {
                            "version": new_version,
                            "author": author,
                            "change_notes": change_notes,
                            "created_at": datetime.now().isoformat()
                        }
                    ]
                }
                
                # Update existing metadata if available
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, "r") as f:
                            existing_metadata = json.load(f)
                            
                            # Update current version
                            existing_metadata["current_version"] = new_version
                            
                            # Add new version info
                            existing_metadata["versions"].append({
                                "version": new_version,
                                "author": author,
                                "change_notes": change_notes,
                                "created_at": datetime.now().isoformat()
                            })
                            
                            metadata = existing_metadata
                    except Exception as e:
                        logger.error(f"Error updating template metadata file: {e}")
                
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                logger.error(f"Error storing template in filesystem: {e}")
        
        return new_version
    
    async def compare_versions(self, template_name: str, version1: int, version2: int) -> str:
        """Compare two versions of a template.
        
        Args:
            template_name: Template name
            version1: First version
            version2: Second version
            
        Returns:
            Unified diff of the templates
        """
        template1 = await self.get_template(template_name, version1)
        template2 = await self.get_template(template_name, version2)
        
        if not template1 or not template2:
            return "One or both templates not found"
        
        # Generate diff
        diff = difflib.unified_diff(
            template1.content.splitlines(keepends=True),
            template2.content.splitlines(keepends=True),
            fromfile=f"{template_name} v{version1}",
            tofile=f"{template_name} v{version2}"
        )
        
        return "".join(diff)
    
    async def register_effectiveness(
        self, 
        template_name: str, 
        version: int, 
        score: float, 
        success: bool = True
    ):
        """Register effectiveness metrics for a template version.
        
        Args:
            template_name: Template name
            version: Template version
            score: Effectiveness score (0-1)
            success: Whether the template usage was successful
        """
        if self.use_db:
            try:
                template_doc = await get_collection("prompt_templates").find_one(
                    {"name": template_name, "version": version}
                )
                
                if not template_doc:
                    logger.warning(f"Template not found: {template_name} v{version}")
                    return
                
                metrics = template_doc.get("effectiveness_metrics", {})
                uses = metrics.get("uses", 0) + 1
                successes = metrics.get("successes", 0)
                
                if success:
                    successes += 1
                
                current_avg = metrics.get("avg_score")
                if current_avg is None:
                    new_avg = score
                else:
                    new_avg = (current_avg * (uses - 1) + score) / uses
                
                await get_collection("prompt_templates").update_one(
                    {"name": template_name, "version": version},
                    {"$set": {
                        "effectiveness_metrics.avg_score": new_avg,
                        "effectiveness_metrics.uses": uses,
                        "effectiveness_metrics.successes": successes,
                        "effectiveness_metrics.success_rate": successes / uses
                    }}
                )
            except Exception as e:
                logger.error(f"Error updating template effectiveness metrics: {e}")
        
        # Update metrics in filesystem if available
        if self.templates_dir:
            metadata_path = os.path.join(self.templates_dir, f"{template_name}.metadata.json")
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    
                    # Find version in metadata
                    for v in metadata.get("versions", []):
                        if v.get("version") == version:
                            metrics = v.get("effectiveness_metrics", {})
                            uses = metrics.get("uses", 0) + 1
                            successes = metrics.get("successes", 0)
                            
                            if success:
                                successes += 1
                            
                            current_avg = metrics.get("avg_score")
                            if current_avg is None:
                                new_avg = score
                            else:
                                new_avg = (current_avg * (uses - 1) + score) / uses
                            
                            v["effectiveness_metrics"] = {
                                "avg_score": new_avg,
                                "uses": uses,
                                "successes": successes,
                                "success_rate": successes / uses
                            }
                            break
                    
                    with open(metadata_path, "w") as f:
                        json.dump(metadata, f, indent=2)
                except Exception as e:
                    logger.error(f"Error updating template effectiveness metrics in filesystem: {e}")
