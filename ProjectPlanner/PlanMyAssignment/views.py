from django.shortcuts import render, redirect
from django.conf import settings
import tempfile
import os
from datetime import datetime
import json
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.tools.retriever import create_retriever_tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain import LLMChain

from .serializers import ProjectSerializer, GradingSerializer
from .models import Project, Grading

# Create your views here.
def home(request):
    return render(request, "base.html")

def projects(request):
    all_projects = Project.objects.prefetch_related('tasks__steps').all()

    # Pass the project data to the template
    context = {
        'projects': all_projects
    }
    return render(request, 'projects.html', context)

def reviews(request):
    all_gradings = Grading.objects.all()

    # Pass the grading data to the template
    context = {
        'gradings': all_gradings
    }
    return render(request, 'gradings.html', context)

def add_project(request):
    if request.method == "POST":
        uploaded_file = request.FILES['userFile']
        with tempfile.NamedTemporaryFile(delete=False, dir=settings.MEDIA_ROOT, suffix=".pdf") as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        doc_loader = PyMuPDFLoader(file_path=temp_file_path)
        documents = doc_loader.load()
        embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")
        vectorstore = FAISS.from_documents(documents, embeddings_model)
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 6})
        context_system_template = """
        You are an expert project planner and consultant. Your role is to meticulously plan the entire project, ensuring that every aspect is covered thoroughly and systematically. You should:

        1. **Understand the Project Scope**: Carefully review the entire project description, objectives, and deliverables to ensure a deep understanding of the requirements.

        2. **Develop a Work Breakdown Structure (WBS)**: Break down the project into manageable tasks and sub-tasks. Ensure that each task is specific, actionable, and contributes directly to the project's goals. The breakdown should resolve into the smallest possible tasks to facilitate easy management and tracking.

        3. **Provide Detailed Steps and Guidelines**:
            - For each task, outline the steps required to complete it.
            - Include necessary resources, tools, and personnel involved in each task.
            - Identify key milestones and checkpoints to monitor progress.
            - Highlight any dependencies between tasks, ensuring a logical sequence of execution.
            - Provide guided steps on how to complete each task

        4. **Ensure Compliance with Requirements**:
            - Verify that every task aligns with the project’s requirements and constraints.
            - Address all critical aspects, including timelines, budget considerations, and quality standards.

        5. **Final Review and Validation**:
            - After outlining the WBS, perform a thorough review to ensure completeness and accuracy.
            - Validate that the WBS covers all aspects of the project and adheres to the guidelines provided.

        6. **The deadline for the Project is {} and start date is {}.
            - All the tasks must be completed within the given timeline.
            - The date format is %Y-%m-%d.

        7. **The Response must be a only a single structured JSON Object following below criteria
            - A single dictionary object.
            - Dictionary object must have a key names "tasks" (Array of dictionary objects).
            - Each Task dictionary object must have keys "task_id" (Integer), "task_name", "efforts" (Required efforts to complete the task in days), "steps" (Array of Objects - Each object must have a key "step_description" (Step description required to complete the step)), "deadline" (A deadline for each task).

        8. **Apart from the JSON the object, response must not contain any other text. This is highly important!
        The goal is to provide a structured, actionable plan that ensures the successful execution of the project. Ensure that the WBS is clear, detailed, and provides a roadmap that can be easily followed by the project team.
        """.format(request.POST.get("dueDate"), datetime.now().strftime("%Y-%m-%d"))

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", context_system_template),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad")
            ]
        )
        llm = ChatOpenAI(
            model="gpt-4",  # Specify the model you want to use
            temperature=0.7  # Adjust the temperature based on your needs
        )
        doc_retriever = create_retriever_tool(
            retriever,
            "Read_document",
            "Read entire dcoument to build a detailed work break down structure \
            For any information about the project use this tool \
            This tool contains all information about the project"
        )
        tools = [doc_retriever]
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            run_name="Agent"
        )
        chat_history = []

        # Define the input you want the agent to process
        user_input = "Please generate a work breakdown structure for the project described in the PDF."

        # Combine everything into the expected input format
        inputs = {
            "input": user_input,
            "chat_history": chat_history,
            "agent_scratchpad": "",  # This might be required depending on your agent setup
        }
        os.remove(temp_file_path)
        # Execute the agent with the input
        response = agent_executor.invoke(inputs)
        data = json.loads(response['output'])
        data["project_name"] = request.POST.get("projectName")
        data["project_deadline"] = request.POST.get("dueDate")
        serializer = ProjectSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
        return redirect("list_projects")
    return render(request, "add_project.html")

def add_reviewer(request):
    if request.method == "POST":
        embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")

        # Assignment Question
        uploaded_file = request.FILES['assignmentFile']
        with tempfile.NamedTemporaryFile(delete=False, dir=settings.MEDIA_ROOT, suffix=".pdf") as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        doc_loader_assignment = PyMuPDFLoader(file_path=temp_file_path)
        documents_assignment = doc_loader_assignment.load()
        vectorstore = FAISS.from_documents(documents_assignment, embeddings_model)
        Ques_retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 6})
        question_retriever = create_retriever_tool(
            Ques_retriever,
            "Assignment_Tasks",
            "Read entire Assignment to understand the given problem \
            For any information regarding the assignment use this tool \
            This tool contains all information about the assignment"
        )
        os.remove(temp_file_path)

        # Rubrics File
        uploaded_file = request.FILES['rubricsFile']
        with tempfile.NamedTemporaryFile(delete=False, dir=settings.MEDIA_ROOT, suffix=".pdf") as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        doc_loader_sample = Docx2txtLoader(file_path=temp_file_path)
        doc_loader_sample = doc_loader_sample.load()
        vectorstore_rubric = FAISS.from_documents(doc_loader_sample, embeddings_model)
        retriever_rubric = vectorstore_rubric.as_retriever(search_type="similarity", search_kwargs={"k": 6})
        rubric_retriever = create_retriever_tool(
            retriever_rubric,          # The retriever for questions related to marking
            "Marking_Rubric",        # Updated name without spaces
            "Use this tool to read the rubric for understanding how to mark assignments. \
            For information on marking strategies and maintaining consistency, refer to this tool."
        )
        os.remove(temp_file_path)

        # Sample File
        uploaded_file = request.FILES['sampleFile']
        with tempfile.NamedTemporaryFile(delete=False, dir=settings.MEDIA_ROOT, suffix=".pdf") as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        ideal_solution = Docx2txtLoader(file_path=temp_file_path)
        doc_loader_sample = ideal_solution.load()
        vectorstore_solution = FAISS.from_documents(doc_loader_sample, embeddings_model)
        retriever_sample = vectorstore_solution.as_retriever(search_type="similarity", search_kwargs={"k": 6})
        solution_retriever = create_retriever_tool(
            retriever_sample,
            "Sample_answer",
            "Read  Sample Asnwer to understand the ideal answer for the problem \
            For any information regarding the soulution use this tool \
            This tool contains the ideal solution for the given problem"
        )
        os.remove(temp_file_path)

        # Solution File
        uploaded_file = request.FILES['solutionFile']
        with tempfile.NamedTemporaryFile(delete=False, dir=settings.MEDIA_ROOT, suffix=".pdf") as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        doc_loader_require_grading = Docx2txtLoader(file_path=temp_file_path)
        doc_require_grading = doc_loader_require_grading.load()
        vectorstore_require_grading = FAISS.from_documents(doc_require_grading, embeddings_model)
        require_grading = vectorstore_require_grading.as_retriever(search_type="similarity", search_kwargs={"k": 6})
        retriever_require_grading = create_retriever_tool(
            require_grading,
            "requires_grading",
            "Carefully analyse this assignment and provide grading \
            Call the solution_retriever to get the Ideal solution  \
            This tool contains the assignment that requires grading"
        )
        os.remove(temp_file_path)

        context_system_template = """
            System Role: Auto Grading System

            Purpose: The system analyzes student assignments and provides grading based on a reference sample solution. The system should ensure accuracy, fairness, and consistency in evaluating each part of the assignment.

            Process:
            1. **Input Handling**:
            - Accept the student’s assignment submission.
            - Accept the sample solution as a reference for grading.
            - Accept the assignment problem description, including total marks and marks distribution for each part.

            2. **Assignment Analysis**:
            - Parse and understand the problem statement to identify the key requirements and expected outputs.
            - Break down the assignment into parts as specified (e.g., Part A, Part B, etc.).
            - Evaluate each part of the student's submission against the corresponding part of the sample solution.

            3. **Grading Criteria**:
            - Compare the correctness, completeness, and accuracy of each part with the sample solution.
            - Allocate marks for each part based on the correctness and adherence to the expected solution.
            - Deduct marks for errors, omissions, or incorrect solutions, according to the marks distribution.

            4. **Mark Allocation**:
            - Sum up the marks obtained for each part to calculate the total score.
            - Ensure that the total score does not exceed the maximum marks allocated for the assignment.

            5. **Feedback Generation**:
            - Provide specific feedback for each part, indicating where the student excelled or where improvements are needed.
            - Include suggestions for improvement if applicable.

            6. **Output**:
            - Return the total marks awarded and detailed feedback for the student.
            - Ensure that the output is clear, precise, and easy for the student to understand.

            Guidelines:
            - Ensure fairness and consistency in grading.
            - Focus on key aspects such as correctness, clarity, completeness, and adherence to the assignment instructions.
            - Provide constructive feedback to guide student improvement.
        """
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", context_system_template),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad")
            ]
        )
        llm = ChatOpenAI(
            model="gpt-4o-mini",  # Specify the model you want to use
            temperature=0.7  # Adjust the temperature based on your needs
        )
        tools = [question_retriever] + [solution_retriever] + [retriever_require_grading] + [rubric_retriever]
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            run_name="Agent"
        )

        chat_history = []

        user_input = "Please grade the requires grading assignment"
        inputs = {
            "input": user_input,
            "chat_history": chat_history,
            "agent_scratchpad": "",
        }

        response = agent_executor.invoke(inputs)
        print("I got below response")
        print(response['output'])
        # data = extract_json(response['output'])
        data = {
            "description": response['output'],
        }
        data["grader_name"] = request.POST.get("graderName")
        serializer = GradingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
        return redirect("list_gradings")

    return render(request, "add_reviewer.html")

# def extract_json(text):
#     start_marker = "{"
#     end_marker = "}"
    
#     # Find the start and end of the JSON content in the text
#     start_index = text.find(start_marker)
#     end_index = text.rfind(end_marker) + 1
#     json_str = text[start_index:end_index]
#     print("Check below extracted Json")
#     print(json_str)
#     print("Json ends")
#     return json.loads(json_str)