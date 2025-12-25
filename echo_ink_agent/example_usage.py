#!/usr/bin/env python3
"""
Echo Ink Agent - Example Usage Script
Demonstrates how to use Echo Ink Agent for educational document creation
"""

import asyncio
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# For this example, we'll use the document tools directly
# In production, you'd use the full EchoInkAgent class
from document_tools import (
    create_educational_document,
    get_document_template_info,
    convert_document_to_pdf,
    search_documents,
    index_documents,
    validate_document_structure
)


async def demonstrate_echo_ink():
    """Demonstrate Echo Ink Agent capabilities"""
    
    print("🎓 Echo Ink Agent - Educational Document Creation Demo")
    print("=" * 60)
    
    # 1. Show available templates
    print("\n📚 Available Document Templates:")
    template_info = get_document_template_info()
    print(template_info)
    
    # 2. Get detailed info for syllabus template
    print("\n📋 Syllabus Template Details:")
    syllabus_info = get_document_template_info("syllabus")
    print(syllabus_info)
    
    # 3. Create a sample syllabus
    print("\n✏️ Creating Sample Syllabus...")
    syllabus_result = create_educational_document(
        doc_type="syllabus",
        course_code="CS101",
        title="Introduction to Computer Science",
        fields={
            "instructor_name": "Dr. Jane Smith",
            "semester": "Fall 2024",
            "credits": "3",
            "description": "This course introduces fundamental concepts of computer science including programming, algorithms, and data structures.",
            "objectives": """
• Understand basic programming concepts and syntax
• Learn problem-solving techniques using algorithms
• Master fundamental data structures (arrays, lists, trees)
• Develop debugging and testing skills
• Apply programming concepts to real-world problems
            """.strip(),
            "modules": """
**Module 1: Programming Fundamentals (Weeks 1-4)**
- Variables, data types, and operators
- Control structures (if/else, loops)
- Functions and parameters

**Module 2: Data Structures (Weeks 5-8)**
- Arrays and lists
- Dictionaries and sets
- Introduction to object-oriented programming

**Module 3: Algorithms (Weeks 9-12)**
- Searching and sorting algorithms
- Recursion and dynamic programming
- Algorithm analysis and complexity

**Module 4: Applications (Weeks 13-16)**
- File I/O and data processing
- Web development basics
- Final project development
            """.strip(),
            "assessment": """
| Component | Weight | Description |
|-----------|--------|-------------|
| Homework Assignments | 30% | Weekly programming exercises |
| Midterm Exam | 20% | Written exam on concepts |
| Final Project | 25% | Comprehensive programming project |
| Final Exam | 20% | Cumulative written exam |
| Participation | 5% | Class attendance and engagement |
            """.strip(),
            "policies": """
**Attendance Policy:** Regular attendance is expected. More than 3 unexcused absences may result in grade reduction.

**Late Work Policy:** Assignments submitted late will receive a 10% penalty per day, up to 3 days. No work accepted after 3 days without prior arrangement.

**Academic Integrity:** All work must be your own. Collaboration is encouraged for learning, but submitted work must be individual. Plagiarism will result in course failure.

**Accommodations:** Students with documented disabilities should contact the Office of Disability Services to arrange appropriate accommodations.
            """.strip()
        }
    )
    print(syllabus_result)
    
    # 4. Create a sample exam
    print("\n📝 Creating Sample Exam...")
    exam_result = create_educational_document(
        doc_type="exam",
        course_code="CS101",
        title="Midterm Examination",
        fields={
            "course_title": "Introduction to Computer Science",
            "exam_type": "Midterm",
            "exam_date": "October 15, 2024",
            "duration": "90 minutes",
            "total_points": "100",
            "instructions": """
• Read all questions carefully before beginning
• Show all work for partial credit
• No electronic devices except approved calculators
• Ask questions if clarification is needed
            """.strip(),
            "mc_points": "30",
            "sa_points": "40", 
            "ps_points": "30",
            "multiple_choice_questions": """
1. Which of the following is NOT a primitive data type in Python?
   a) int    b) float    c) string    d) list

2. What is the time complexity of binary search?
   a) O(1)    b) O(log n)    c) O(n)    d) O(n²)

3. Which loop structure is best for iterating over a list?
   a) while    b) for    c) do-while    d) repeat-until
            """.strip(),
            "short_answer_questions": """
1. (10 points) Explain the difference between a list and a tuple in Python. Give an example of when you would use each.

2. (15 points) Write a function that takes a list of numbers and returns the sum of all even numbers in the list.

3. (15 points) Describe what happens during each iteration of the following code:
   ```python
   numbers = [1, 2, 3, 4, 5]
   result = []
   for num in numbers:
       if num % 2 == 0:
           result.append(num * 2)
   ```
            """.strip(),
            "problem_solving_questions": """
1. (15 points) Write a complete Python program that:
   - Asks the user to enter 5 numbers
   - Stores them in a list
   - Finds and prints the largest number
   - Calculates and prints the average

2. (15 points) Given the following function, trace through its execution with the input `factorial(4)`:
   ```python
   def factorial(n):
       if n <= 1:
           return 1
       else:
           return n * factorial(n - 1)
   ```
   Show each recursive call and return value.
            """.strip(),
            "answer_key": """
**Multiple Choice:**
1. d) list
2. b) O(log n)  
3. b) for

**Short Answer:**
1. Lists are mutable, tuples are immutable. Use lists for changing data, tuples for fixed data.
2. `def sum_evens(numbers): return sum(num for num in numbers if num % 2 == 0)`
3. Iterates through [1,2,3,4,5], doubles even numbers [2,4], result = [4,8]

**Problem Solving:**
1. [Sample solution with input validation and calculations]
2. factorial(4) → 4 * factorial(3) → 4 * 3 * factorial(2) → 4 * 3 * 2 * factorial(1) → 4 * 3 * 2 * 1 = 24
            """.strip()
        }
    )
    print(exam_result)
    
    # 5. Create a sample assignment
    print("\n📋 Creating Sample Assignment...")
    assignment_result = create_educational_document(
        doc_type="assignment",
        course_code="CS101",
        title="Programming Fundamentals",
        fields={
            "assignment_number": "3",
            "due_date": "September 30, 2024, 11:59 PM",
            "total_points": "50",
            "submission_method": "Submit via course LMS as a .py file",
            "overview": "This assignment focuses on applying control structures and functions to solve practical programming problems.",
            "objectives": """
• Practice using conditional statements and loops
• Implement functions with parameters and return values
• Apply problem-solving strategies to programming challenges
• Debug and test code systematically
            """.strip(),
            "instructions": """
Complete all three problems below. Each problem should be implemented as a separate function. Include a main() function that tests each of your solutions with the provided test cases.

**Submission Requirements:**
- Single Python file named: lastname_firstname_hw3.py
- Include your name and student ID in comments at the top
- Test your code thoroughly before submission
- Follow proper Python naming conventions
            """.strip(),
            "tasks": """
**Problem 1: Grade Calculator (15 points)**
Write a function `calculate_grade(scores)` that takes a list of test scores and returns the letter grade based on the average:
- A: 90-100
- B: 80-89  
- C: 70-79
- D: 60-69
- F: Below 60

**Problem 2: Password Validator (20 points)**
Write a function `is_valid_password(password)` that returns True if a password meets these criteria:
- At least 8 characters long
- Contains at least one uppercase letter
- Contains at least one lowercase letter  
- Contains at least one digit
- Contains at least one special character (!@#$%^&*)

**Problem 3: Number Pattern (15 points)**
Write a function `print_triangle(n)` that prints a number triangle pattern:
```
For n=4:
1
1 2
1 2 3  
1 2 3 4
```
            """.strip(),
            "rubric": """
| Criteria | Excellent (A) | Good (B) | Satisfactory (C) | Needs Work (D/F) |
|----------|---------------|----------|------------------|------------------|
| **Correctness** | All test cases pass | Most test cases pass | Some test cases pass | Few/no test cases pass |
| **Code Quality** | Clean, readable, well-commented | Mostly clean and readable | Adequate structure | Poor structure/readability |
| **Problem Solving** | Efficient, elegant solutions | Good solutions with minor issues | Basic working solutions | Incomplete or incorrect approach |
| **Testing** | Comprehensive test cases | Good test coverage | Basic testing | Minimal/no testing |
            """.strip(),
            "resources": """
• Python documentation: https://docs.python.org/3/
• Course textbook: Chapters 3-5
• Office hours: Tuesdays 2-4 PM, Thursdays 10-12 PM
• Online Python tutor: http://pythontutor.com/
            """.strip()
        }
    )
    print(assignment_result)
    
    # 6. Show document management features
    print("\n📁 Document Management Features:")
    
    # Index all documents
    print("\n📊 Document Index:")
    index_result = index_documents()
    print(index_result)
    
    # Search for documents
    print("\n🔍 Searching for 'CS101' documents:")
    search_result = search_documents("CS101")
    print(search_result)
    
    # Validate a document (if it exists)
    docs_dir = Path("documents")
    if docs_dir.exists():
        md_files = list(docs_dir.glob("*.md"))
        if md_files:
            print(f"\n✅ Validating document: {md_files[0].name}")
            validation_result = validate_document_structure(str(md_files[0]))
            print(validation_result)
    
    # 7. Demonstrate PDF conversion (if Pandoc is available)
    print("\n📄 PDF Conversion Demo:")
    if docs_dir.exists():
        md_files = list(docs_dir.glob("*.md"))
        if md_files:
            pdf_result = convert_document_to_pdf(str(md_files[0]))
            print(pdf_result)
    
    print("\n🎉 Demo Complete!")
    print("Check the 'documents' directory for generated files.")


if __name__ == "__main__":
    asyncio.run(demonstrate_echo_ink())