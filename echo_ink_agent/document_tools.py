"""
Custom document creation tools for Echo Ink Agent
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from strands import tool
from templates import (
    get_template, 
    get_template_info, 
    validate_template_fields,
    populate_template,
    generate_filename,
    list_template_types
)

logger = logging.getLogger(__name__)


@tool
def create_educational_document(
    doc_type: str,
    course_code: str, 
    title: str,
    fields: Dict[str, Any]
) -> str:
    """
    Create an educational document from a template with smart field population.
    
    Args:
        doc_type: Type of document (syllabus, exam, assignment, lecture, class_content, lab)
        course_code: Course identifier (e.g., "CS101", "MATH201")
        title: Document title
        fields: Dictionary of field values to populate the template
        
    Returns:
        str: Success message with filename and path
        
    Examples:
        create_educational_document(
            "syllabus",
            "CS101", 
            "Introduction to Computer Science",
            {
                "instructor_name": "Dr. Smith",
                "semester": "Fall 2024",
                "credits": "3",
                "description": "Fundamentals of programming and computer science"
            }
        )
    """
    try:
        # Validate document type
        template = get_template(doc_type)
        if not template:
            available_types = ", ".join(list_template_types())
            return f"❌ Error: Unknown document type '{doc_type}'. Available types: {available_types}"
        
        # Validate required fields
        is_valid, missing_fields = validate_template_fields(doc_type, fields)
        if not is_valid:
            return f"❌ Error: Missing required fields: {', '.join(missing_fields)}"
        
        # Generate content
        content = populate_template(template, fields, course_code, title)
        
        # Generate filename
        filename = generate_filename(course_code, doc_type, title)
        
        # Ensure documents directory exists
        docs_dir = Path("documents")
        docs_dir.mkdir(exist_ok=True)
        
        # Write file
        file_path = docs_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created document: {file_path}")
        
        return f"✅ Successfully created {template['name']}: {filename}\n📁 Location: {file_path}\n📄 Content preview:\n{content[:200]}..."
        
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        return f"❌ Error creating document: {str(e)}"


@tool
def convert_document_to_pdf(markdown_file: str) -> str:
    """
    Convert a Markdown document to PDF using Pandoc.
    
    Args:
        markdown_file: Path to the Markdown file to convert
        
    Returns:
        str: Success message with PDF path or error message
        
    Examples:
        convert_document_to_pdf("documents/CS101_Syllabus_Intro_DRAFT.md")
    """
    try:
        # Validate input file
        md_path = Path(markdown_file)
        if not md_path.exists():
            return f"❌ Error: Markdown file not found: {markdown_file}"
        
        if not md_path.suffix.lower() in ['.md', '.markdown']:
            return f"❌ Error: File must be a Markdown file (.md or .markdown): {markdown_file}"
        
        # Generate PDF filename
        pdf_path = md_path.with_suffix('.pdf')
        
        # Check if pandoc is available
        try:
            subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "❌ Error: Pandoc is not installed. Please install Pandoc to convert to PDF."
        
        # Convert to PDF using pandoc
        cmd = [
            'pandoc',
            str(md_path),
            '-o', str(pdf_path),
            '--pdf-engine=xelatex',  # Use XeLaTeX for better formatting
            '-V', 'geometry:margin=1in',  # Set margins
            '--highlight-style=tango',  # Syntax highlighting
            '--toc',  # Table of contents
            '--number-sections'  # Number sections
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Converted to PDF: {pdf_path}")
            return f"✅ Successfully converted to PDF: {pdf_path.name}\n📁 Location: {pdf_path}"
        else:
            return f"❌ Error converting to PDF: {result.stderr}"
            
    except Exception as e:
        logger.error(f"Error converting to PDF: {e}")
        return f"❌ Error converting to PDF: {str(e)}"


@tool
def get_document_template_info(doc_type: str = None) -> str:
    """
    Get information about document templates, including required and optional fields.
    
    Args:
        doc_type: Specific document type to get info for, or None to list all types
        
    Returns:
        str: Template information formatted for display
        
    Examples:
        get_document_template_info("syllabus")
        get_document_template_info()  # Lists all templates
    """
    try:
        if doc_type is None:
            # List all available templates
            templates = list_template_types()
            info = "📚 Available Document Templates:\n\n"
            
            for template_type in templates:
                template_info = get_template_info(template_type)
                info += f"**{template_info['name']}** (`{template_type}`)\n"
                info += f"   {template_info['description']}\n"
                info += f"   Required fields: {len(template_info['required_fields'])}\n\n"
            
            info += "💡 Use get_document_template_info('template_type') for detailed field information."
            return info
        
        else:
            # Get specific template info
            template_info = get_template_info(doc_type)
            if not template_info:
                available_types = ", ".join(list_template_types())
                return f"❌ Error: Unknown template type '{doc_type}'. Available types: {available_types}"
            
            info = f"📋 **{template_info['name']}** Template\n\n"
            info += f"**Description:** {template_info['description']}\n\n"
            
            info += "**Required Fields:**\n"
            for field in template_info['required_fields']:
                info += f"   • {field.replace('_', ' ').title()}\n"
            
            if template_info['optional_fields']:
                info += "\n**Optional Fields:**\n"
                for field in template_info['optional_fields']:
                    info += f"   • {field.replace('_', ' ').title()}\n"
            
            info += f"\n💡 Use create_educational_document('{doc_type}', course_code, title, fields) to create this document."
            
            return info
            
    except Exception as e:
        logger.error(f"Error getting template info: {e}")
        return f"❌ Error getting template info: {str(e)}"


@tool
def search_documents(query: str, doc_type: str = None) -> str:
    """
    Search through created documents for specific content.
    
    Args:
        query: Search term or phrase
        doc_type: Optional document type to filter by
        
    Returns:
        str: Search results with file paths and matching content
        
    Examples:
        search_documents("assignment")
        search_documents("midterm", "exam")
    """
    try:
        docs_dir = Path("documents")
        if not docs_dir.exists():
            return "📁 No documents directory found. Create some documents first!"
        
        results = []
        search_pattern = f"*{doc_type}*" if doc_type else "*"
        
        for file_path in docs_dir.glob(f"{search_pattern}.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if query.lower() in content.lower():
                    # Find the line containing the query
                    lines = content.split('\n')
                    matching_lines = [
                        (i+1, line) for i, line in enumerate(lines) 
                        if query.lower() in line.lower()
                    ]
                    
                    results.append({
                        'file': file_path.name,
                        'path': str(file_path),
                        'matches': matching_lines[:3]  # Limit to first 3 matches
                    })
                    
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
                continue
        
        if not results:
            return f"🔍 No documents found containing '{query}'"
        
        # Format results
        output = f"🔍 Found {len(results)} document(s) containing '{query}':\n\n"
        
        for result in results:
            output += f"📄 **{result['file']}**\n"
            output += f"   📁 {result['path']}\n"
            
            for line_num, line in result['matches']:
                # Highlight the query term (simple text highlighting)
                highlighted_line = line.replace(
                    query, f"**{query}**"
                ).replace(
                    query.lower(), f"**{query.lower()}**"
                ).replace(
                    query.upper(), f"**{query.upper()}**"
                )
                output += f"   Line {line_num}: {highlighted_line.strip()}\n"
            
            output += "\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return f"❌ Error searching documents: {str(e)}"


@tool
def index_documents() -> str:
    """
    Create an index of all documents in the documents directory.
    
    Returns:
        str: Formatted index of all documents with metadata
        
    Examples:
        index_documents()
    """
    try:
        docs_dir = Path("documents")
        if not docs_dir.exists():
            return "📁 No documents directory found. Create some documents first!"
        
        # Get all markdown files
        md_files = list(docs_dir.glob("*.md"))
        pdf_files = list(docs_dir.glob("*.pdf"))
        
        if not md_files and not pdf_files:
            return "📁 No documents found in the documents directory."
        
        # Create index
        index = f"📚 Document Index ({len(md_files + pdf_files)} files)\n"
        index += f"📁 Location: {docs_dir.absolute()}\n\n"
        
        if md_files:
            index += "**Markdown Documents:**\n"
            for file_path in sorted(md_files):
                # Get file stats
                stat = file_path.stat()
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                
                # Try to extract document type from filename
                name_parts = file_path.stem.split('_')
                doc_type = name_parts[1] if len(name_parts) > 1 else "Unknown"
                
                index += f"   📄 {file_path.name}\n"
                index += f"      Type: {doc_type} | Size: {size:,} bytes | Modified: {modified}\n"
            
            index += "\n"
        
        if pdf_files:
            index += "**PDF Documents:**\n"
            for file_path in sorted(pdf_files):
                # Get file stats
                stat = file_path.stat()
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                
                index += f"   📄 {file_path.name}\n"
                index += f"      Size: {size:,} bytes | Modified: {modified}\n"
            
            index += "\n"
        
        # Add summary statistics
        total_size = sum(f.stat().st_size for f in md_files + pdf_files)
        index += f"📊 **Summary:** {len(md_files)} Markdown, {len(pdf_files)} PDF files | Total size: {total_size:,} bytes"
        
        return index
        
    except Exception as e:
        logger.error(f"Error indexing documents: {e}")
        return f"❌ Error indexing documents: {str(e)}"


@tool
def validate_document_structure(file_path: str) -> str:
    """
    Validate the structure and content of an educational document.
    
    Args:
        file_path: Path to the document to validate
        
    Returns:
        str: Validation results with suggestions for improvement
        
    Examples:
        validate_document_structure("documents/CS101_Syllabus_Intro_DRAFT.md")
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"❌ Error: File not found: {file_path}"
        
        if not path.suffix.lower() in ['.md', '.markdown']:
            return f"❌ Error: File must be a Markdown file: {file_path}"
        
        # Read content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Validation checks
        issues = []
        suggestions = []
        
        # Check for title (should start with #)
        if not any(line.strip().startswith('#') for line in lines[:5]):
            issues.append("No main title found (should start with #)")
        
        # Check for empty sections
        empty_sections = []
        current_section = None
        section_content = []
        
        for line in lines:
            if line.strip().startswith('#'):
                if current_section and not any(section_content):
                    empty_sections.append(current_section)
                current_section = line.strip()
                section_content = []
            elif line.strip():
                section_content.append(line.strip())
        
        if empty_sections:
            issues.append(f"Empty sections found: {', '.join(empty_sections)}")
        
        # Check document length
        word_count = len(content.split())
        if word_count < 100:
            suggestions.append("Document seems short - consider adding more detail")
        elif word_count > 5000:
            suggestions.append("Document is quite long - consider breaking into sections")
        
        # Check for placeholder text
        placeholders = [line for line in lines if '[' in line and ']' in line]
        if placeholders:
            issues.append(f"Placeholder text found: {len(placeholders)} instances")
        
        # Format results
        result = f"📋 **Document Validation: {path.name}**\n\n"
        result += f"📊 **Statistics:**\n"
        result += f"   • Word count: {word_count:,}\n"
        result += f"   • Line count: {len(lines):,}\n"
        result += f"   • File size: {path.stat().st_size:,} bytes\n\n"
        
        if issues:
            result += "⚠️ **Issues Found:**\n"
            for issue in issues:
                result += f"   • {issue}\n"
            result += "\n"
        
        if suggestions:
            result += "💡 **Suggestions:**\n"
            for suggestion in suggestions:
                result += f"   • {suggestion}\n"
            result += "\n"
        
        if not issues and not suggestions:
            result += "✅ **Document looks good!** No issues found.\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating document: {e}")
        return f"❌ Error validating document: {str(e)}"