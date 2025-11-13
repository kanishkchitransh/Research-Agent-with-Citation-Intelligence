"""Core Research Agent implementation using ReAct pattern with Gemini."""

import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from loguru import logger

from .prompts import get_system_prompt
from .tools import ToolRegistry


class AgentStep:
    """Represents one step in the agent's reasoning process."""

    def __init__(
        self,
        step_num: int,
        thought: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict] = None,
        tool_output: Optional[str] = None,
    ):
        self.step_num = step_num
        self.thought = thought
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_output = tool_output

    def __repr__(self) -> str:
        return f"Step {self.step_num}: {self.tool_name}({self.tool_input}) -> {self.tool_output[:100] if self.tool_output else 'None'}..."


class AgentResponse:
    """The agent's final response."""

    def __init__(
        self,
        answer: str,
        steps: List[AgentStep],
        success: bool = True,
        error: Optional[str] = None,
    ):
        self.answer = answer
        self.steps = steps
        self.success = success
        self.error = error

    def __repr__(self) -> str:
        return f"AgentResponse(steps={len(self.steps)}, success={self.success})"


class ResearchAgent:
    """
    Research Agent using ReAct pattern with Gemini.

    The agent can:
    - Answer questions about research papers
    - Search across multiple papers
    - Explain citations and their context
    - Perform multi-step reasoning
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        max_iterations: int = 10,
        temperature: float = 0.7,
        verbose: bool = True,
    ):
        """
        Initialize the Research Agent.

        Args:
            tool_registry: Registry of available tools
            api_key: Google AI API key
            model_name: Name of the Gemini model to use
            max_iterations: Maximum number of reasoning iterations
            temperature: Model temperature
            verbose: Whether to log verbose output
        """
        self.tool_registry = tool_registry
        self.model_name = model_name
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.verbose = verbose

        # Configure Gemini
        genai.configure(api_key=api_key)

        # Initialize model with function calling
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=[self._convert_tools_for_gemini()],
            system_instruction=get_system_prompt(),
        )

        logger.info(
            f"ResearchAgent initialized with {model_name} "
            f"(max_iterations={max_iterations}, tools={len(tool_registry.tools)})"
        )

    def _convert_tools_for_gemini(self) -> List[Any]:
        """Convert tools to Gemini function declarations."""
        tools = []
        for tool in self.tool_registry.get_all_tools():
            # Create function declaration
            func_decl = genai.protos.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        param_name: genai.protos.Schema(
                            type=self._get_type(param_info.get("type", "string")),
                            description=param_info.get("description", ""),
                        )
                        for param_name, param_info in tool.parameters.get(
                            "properties", {}
                        ).items()
                    },
                    required=tool.parameters.get("required", []),
                ),
            )
            tools.append(func_decl)

        return tools

    def _get_type(self, type_str: str) -> genai.protos.Type:
        """Convert JSON schema type to Gemini type."""
        type_mapping = {
            "string": genai.protos.Type.STRING,
            "integer": genai.protos.Type.INTEGER,
            "number": genai.protos.Type.NUMBER,
            "boolean": genai.protos.Type.BOOLEAN,
            "object": genai.protos.Type.OBJECT,
            "array": genai.protos.Type.ARRAY,
        }
        return type_mapping.get(type_str.lower(), genai.protos.Type.STRING)

    def query(self, question: str) -> AgentResponse:
        """
        Query the agent with a question.

        Args:
            question: The user's question

        Returns:
            AgentResponse with the answer and reasoning steps
        """
        logger.info(f"Agent received query: {question}")

        try:
            # Start chat session
            chat = self.model.start_chat(enable_automatic_function_calling=False)

            # Send initial question
            response = chat.send_message(question)

            steps = []
            iteration = 0

            # ReAct loop
            while iteration < self.max_iterations:
                iteration += 1

                # Check if the model wants to call a function
                if response.candidates[0].content.parts:
                    part = response.candidates[0].content.parts[0]

                    # Check if it's a function call
                    if hasattr(part, "function_call") and part.function_call:
                        function_call = part.function_call
                        tool_name = function_call.name

                        # Extract arguments
                        tool_args = {}
                        for key, value in function_call.args.items():
                            tool_args[key] = value

                        if self.verbose:
                            logger.info(
                                f"Step {iteration}: Calling {tool_name} with {tool_args}"
                            )

                        # Execute the tool
                        tool = self.tool_registry.get_tool(tool_name)
                        if not tool:
                            logger.error(f"Tool {tool_name} not found")
                            return AgentResponse(
                                answer="",
                                steps=steps,
                                success=False,
                                error=f"Tool {tool_name} not found",
                            )

                        try:
                            tool_output = tool(**tool_args)

                            # Record step
                            step = AgentStep(
                                step_num=iteration,
                                tool_name=tool_name,
                                tool_input=tool_args,
                                tool_output=str(tool_output),
                            )
                            steps.append(step)

                            if self.verbose:
                                logger.info(
                                    f"Step {iteration}: {tool_name} returned {len(str(tool_output))} chars"
                                )

                            # Send tool result back to model
                            response = chat.send_message(
                                genai.protos.Content(
                                    parts=[
                                        genai.protos.Part(
                                            function_response=genai.protos.FunctionResponse(
                                                name=tool_name,
                                                response={"result": str(tool_output)},
                                            )
                                        )
                                    ]
                                )
                            )

                        except Exception as e:
                            logger.error(f"Error executing tool {tool_name}: {e}")
                            return AgentResponse(
                                answer="",
                                steps=steps,
                                success=False,
                                error=f"Error executing tool: {str(e)}",
                            )

                    # Check if it's a text response (final answer)
                    elif hasattr(part, "text") and part.text:
                        answer = part.text

                        if self.verbose:
                            logger.info(
                                f"Agent completed in {iteration} steps with {len(answer)} char answer"
                            )

                        return AgentResponse(
                            answer=answer,
                            steps=steps,
                            success=True,
                        )

                else:
                    # No more parts, likely done
                    answer = response.text if hasattr(response, "text") else ""
                    return AgentResponse(
                        answer=answer,
                        steps=steps,
                        success=True,
                    )

            # Max iterations reached
            logger.warning(f"Agent reached max iterations ({self.max_iterations})")
            return AgentResponse(
                answer="Maximum iterations reached. Unable to complete the task fully.",
                steps=steps,
                success=False,
                error="Max iterations reached",
            )

        except Exception as e:
            logger.error(f"Error in agent query: {e}")
            return AgentResponse(
                answer="",
                steps=[],
                success=False,
                error=str(e),
            )

    def chat(self, question: str, chat_history: Optional[List[Dict[str, str]]] = None) -> AgentResponse:
        """
        Chat with the agent (maintains conversation context).

        Args:
            question: The user's question
            chat_history: Optional previous chat messages

        Returns:
            AgentResponse with the answer and reasoning steps
        """
        # For now, just call query (can be extended later for multi-turn conversations)
        return self.query(question)

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "model": self.model_name,
            "max_iterations": self.max_iterations,
            "num_tools": len(self.tool_registry.tools),
            "tools": list(self.tool_registry.tools.keys()),
        }
