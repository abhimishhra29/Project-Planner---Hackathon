from django.shortcuts import render, redirect
from django.conf import settings
import tempfile
import os
from datetime import datetime
import json
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.document_loaders import PyMuPDFLoader
from langchain.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.tools.retriever import create_retriever_tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain import LLMChain

from .serializers import ProjectSerializer
from .models import Project

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
