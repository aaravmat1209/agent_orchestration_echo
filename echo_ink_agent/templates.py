"""
Document template definitions for Echo Ink Agent
Templates are Python data structures for better maintainability and testability
"""

from typing import Dict, List

# ============================================================================
# Template Registry
# ============================================================================

TEMPLATES = {
    "syllabus": {
        "name": "Course Syllabus",
        "description": "Comprehensive course overview and structure",
        "structure": """# {course_code} - {title}

**Instructor:** {instructor_name}
**Semester:** {semester}
**Credits:** {credits}

## Course Description
{description}

## Learning Objectives
{objectives}

## Course Modules
{modules}

## Assessment
{assessment}

## Schedule
{schedule}

## Course Policies
{policies}
""",
        "required_fields": ["instructor_name", "semester", "credits", "description"],
        "optional_fields": ["objectives", "modules", "assessment", "schedule", "policies"]
    },

    "exam": {
        "name": "Sample Exam",
        "description": "Comprehensive exam with multiple sections",
        "structure": """# {course_code} - {title}

**Course:** {course_title}
**Exam:** {exam_type}
**Date:** {exam_date}
**Duration:** {duration}
**Total Points:** {total_points}

## Instructions
{instructions}

## Section A: Multiple Choice ({mc_points} points)
*Choose the best answer for each question.*

{multiple_choice_questions}

## Section B: Short Answer ({sa_points} points)
*Provide brief, clear answers.*

{short_answer_questions}

## Section C: Problem Solving ({ps_points} points)
*Show all work and explain your reasoning.*

{problem_solving_questions}

## Answer Key
*For instructor use*

{answer_key}
""",
        "required_fields": ["course_title", "exam_type", "duration", "total_points"],
        "optional_fields": ["exam_date", "instructions", "mc_points", "sa_points", "ps_points",
                          "multiple_choice_questions", "short_answer_questions",
                          "problem_solving_questions", "answer_key"]
    },

    "assignment": {
        "name": "Assignment",
        "description": "Homework or project assignment",
        "structure": """# Assignment {assignment_number}: {title}

**Course:** {course_code}
**Due Date:** {due_date}
**Points:** {total_points}
**Submission:** {submission_method}

## Overview
{overview}

## Learning Objectives
Students will demonstrate ability to:
{objectives}

## Instructions
{instructions}

## Requirements
{requirements}

## Problems/Tasks
{tasks}

## Grading Rubric
{rubric}

## Submission Guidelines
{submission_guidelines}

## Resources
{resources}
""",
        "required_fields": ["assignment_number", "due_date", "total_points", "overview"],
        "optional_fields": ["submission_method", "objectives", "instructions", "requirements",
                          "tasks", "rubric", "submission_guidelines", "resources"]
    },

    "lecture": {
        "name": "Lecture Notes",
        "description": "Detailed lecture notes for class",
        "structure": """# Lecture {lecture_number}: {title}

**Course:** {course_code}
**Date:** {lecture_date}
**Chapter:** {chapter_reference}

## Today's Agenda
{agenda}

## Learning Objectives
{objectives}

## Review from Last Class
{review}

## Main Content

{main_content}

## Summary
{summary}

## Next Class Preview
{next_class}

## Homework/Practice
{homework}
""",
        "required_fields": ["lecture_number", "lecture_date", "main_content"],
        "optional_fields": ["chapter_reference", "agenda", "objectives", "review",
                          "summary", "next_class", "homework"]
    },

    "class_content": {
        "name": "Class Content",
        "description": "Daily class session content",
        "structure": """# {title} - Class {class_number}

**Course:** {course_code}
**Date:** {class_date}
**Duration:** {duration}

## Learning Objectives
By the end of this class, students will be able to:
{objectives}

## Prerequisites
{prerequisites}

## Class Outline

### Introduction ({intro_duration} minutes)
{introduction}

### Main Content ({main_duration} minutes)
{main_content}

### Practice/Activity ({activity_duration} minutes)
{activities}

### Wrap-up ({wrapup_duration} minutes)
{wrapup}

## Key Concepts
{key_concepts}

## Resources
{resources}

## Homework/Next Steps
{homework}
""",
        "required_fields": ["class_number", "class_date", "duration", "objectives"],
        "optional_fields": ["prerequisites", "intro_duration", "main_duration",
                          "activity_duration", "wrapup_duration", "introduction",
                          "main_content", "activities", "wrapup", "key_concepts",
                          "resources", "homework"]
    },

    "lab": {
        "name": "Lab Manual",
        "description": "Hands-on lab exercise manual",
        "structure": """# Lab {lab_number}: {title}

**Course:** {course_code}
**Duration:** {duration}
**Difficulty:** {difficulty}

## Objectives
Students will:
{objectives}

## Prerequisites
{prerequisites}

## Materials Needed
{materials}

## Safety Guidelines
{safety}

## Procedure

### Part 1: Setup ({setup_duration} minutes)
{setup_steps}

### Part 2: Main Exercise ({exercise_duration} minutes)
{exercise_steps}

### Part 3: Analysis ({analysis_duration} minutes)
{analysis_steps}

## Deliverables
{deliverables}

## Troubleshooting
{troubleshooting}

## Extension Activities
{extensions}
""",
        "required_fields": ["lab_number", "duration", "objectives", "exercise_steps"],
        "optional_fields": ["difficulty", "prerequisites", "materials", "safety",
                          "setup_duration", "exercise_duration", "analysis_duration",
                          "setup_steps", "analysis_steps", "deliverables",
                          "troubleshooting", "extensions"]
    }
}


# ============================================================================
# Template Helper Functions
# ============================================================================

def get_template(doc_type: str) -> Dict:
    """
    Get template definition for a document type

    Args:
        doc_type: Type of document (syllabus, exam, assignment, etc.)

    Returns:
        dict: Template definition or None if not found
    """
    return TEMPLATES.get(doc_type)


def list_template_types() -> List[str]:
    """Get list of available template types"""
    return list(TEMPLATES.keys())


def get_template_info(doc_type: str) -> Dict:
    """
    Get template metadata

    Args:
        doc_type: Type of document

    Returns:
        dict: Template name, description, required fields
    """
    template = TEMPLATES.get(doc_type)
    if not template:
        return None

    return {
        "doc_type": doc_type,
        "name": template["name"],
        "description": template["description"],
        "required_fields": template["required_fields"],
        "optional_fields": template.get("optional_fields", [])
    }


def validate_template_fields(doc_type: str, fields: Dict) -> tuple:
    """
    Validate that required fields are present

    Args:
        doc_type: Type of document
        fields: Dictionary of fields to validate

    Returns:
        tuple: (is_valid: bool, missing_fields: list)
    """
    template = TEMPLATES.get(doc_type)
    if not template:
        return False, [f"Unknown template type: {doc_type}"]

    required_fields = template["required_fields"]
    missing_fields = [field for field in required_fields if field not in fields]

    return len(missing_fields) == 0, missing_fields


def populate_template(template: Dict, fields: Dict, course_code: str, title: str) -> str:
    """
    Populate template with fields

    Args:
        template: Template definition
        fields: Dictionary of field values
        course_code: Course identifier
        title: Document title

    Returns:
        str: Populated template content
    """
    structure = template["structure"]

    # Add default fields
    fields["course_code"] = course_code
    fields["title"] = title

    # Fill optional fields with defaults
    for field in template.get("optional_fields", []):
        if field not in fields:
            fields[field] = f"[{field.replace('_', ' ').title()}]"

    # Format template
    try:
        return structure.format(**fields)
    except KeyError as e:
        raise ValueError(f"Missing required field: {e}")


def generate_filename(course_code: str, doc_type: str, title: str = None) -> str:
    """
    Generate standardized filename for document

    Args:
        course_code: Course identifier
        doc_type: Document type
        title: Optional title for filename

    Returns:
        str: Filename in format: {CourseCode}_{DocType}_{Title}_DRAFT.md
    """
    from datetime import datetime

    # Clean doc type for filename
    clean_type = doc_type.replace("_", "").title()

    # Add title if provided
    if title:
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
        clean_title = clean_title.replace(" ", "_")[:30]  # Limit length
        filename = f"{course_code}_{clean_type}_{clean_title}_DRAFT.md"
    else:
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{course_code}_{clean_type}_{timestamp}_DRAFT.md"

    return filename
