"""
Predefined workflows for common analysis scenarios.

This package contains workflow configurations for common analysis scenarios,
such as project analysis, contract analysis, etc.
"""

from .project_analysis_workflow import create_project_analysis_workflow

__all__ = ['create_project_analysis_workflow']
