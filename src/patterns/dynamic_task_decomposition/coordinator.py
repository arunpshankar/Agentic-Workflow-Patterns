import asyncio
from typing import List, Any
import json
from src.patterns.dynamic_task_decomposition.agent import Agent
from src.patterns.dynamic_task_decomposition.delegates import SubTaskAgent
from src.patterns.dynamic_task_decomposition.message import Message
from src.llm.generate import ResponseGenerator
from src.config.logging import logger

class CoordinatorAgent(Agent):
    """
    An agent that coordinates the processing of a book by decomposing the main task
    into subtasks using an LLM and assigning them to sub-agents to execute in parallel.
    """

    def __init__(self, name: str) -> None:
        """
        Initializes the CoordinatorAgent with a given name.

        Args:
            name (str): The name of the coordinator agent.
        """
        super().__init__(name)
        logger.info(f"{self.name} initialized.")

    async def process(self, message: Message) -> Message:
        """
        Processes the main task by decomposing it into subtasks, 
        assigning those subtasks to sub-agents, and combining their results.

        Args:
            message (Message): The message containing the task to process.

        Returns:
            Message: The final result message after processing.
        """
        logger.info(f"{self.name} processing message.")
        try:
            book_content = message.content  # The content of the book

            # Decompose the main task into subtasks using the LLM
            subtasks = await self.decompose_task(book_content)

            # Create sub-agents and execute subtasks in parallel
            tasks = []
            for idx, subtask in subtasks.items():  # Use items() to iterate over key-value pairs
                agent_name = f"SubTaskAgent_{idx}"
                agent = SubTaskAgent(name=agent_name)
                logger.info(f"Assigning subtask: {subtask} to {agent_name}")
                
                sub_message = Message(
                    content={"book": book_content, "task": subtask},
                    sender=self.name,
                    recipient=agent_name
                )
                task = asyncio.create_task(agent.process(sub_message))
                tasks.append(task)

            # Gather results from all sub-agents concurrently
            sub_results = await asyncio.gather(*tasks)

            # Combine the results into a structured document, preserving the order of subtasks
            combined_result = self.combine_results(sub_results, subtasks)

            # Return the final message with the combined result
            return Message(content=combined_result, sender=self.name, recipient=message.sender)

        except Exception as e:
            logger.error(f"Error during processing: {str(e)}")
            return Message(
                content="An error occurred while processing the book.",
                sender=self.name,
                recipient=message.sender
            )

    async def decompose_task(self, book_content: str) -> dict:
        """
        Uses an LLM to deduce exactly 10 independent subtasks from the main task.

        Args:
            book_content (str): The content of the book to analyze.

        Returns:
            dict: A dictionary of independent subtasks in the format {'task_1': 'subtask description', ...}.
        """
        logger.info("Decomposing main task into subtasks using LLM.")

        # Prepare the refined prompt for the LLM with the JSON output request
        llm_input = (
            "You are an expert in literary analysis. Given the text of a book, generate exactly 10 independent "
            "extraction tasks that can be executed in parallel. The tasks should focus on extracting different "
            "types of entities such as characters, locations, themes, plot points, and more. The output should be "
            "a JSON object with keys 'task_1', 'task_2', ..., and corresponding task descriptions as values. "
            "Do not include tasks that require math operations like counts and frequency.\n\n"
            "Book Text:\n"
            f"{book_content}"
        )

        try:
            response_generator = ResponseGenerator()

            # Define a blocking function to be run in a separate thread
            def blocking_call():
                return response_generator.generate_response(
                    model_name='gemini-1.5-flash-001',
                    system_instruction='',
                    contents=[llm_input]
                ).text.strip()

            # Run the blocking LLM call in a separate thread
            decomposition_result = await asyncio.to_thread(blocking_call)

            # Parse the decomposition result into a dictionary of subtasks
            subtasks = self.parse_subtasks(decomposition_result)

            logger.info(f"Subtasks generated by LLM: {subtasks}")

            return subtasks

        except Exception as e:
            logger.error(f"Failed to decompose task: {str(e)}")
            raise

    def parse_subtasks(self, decomposition_result: str) -> dict:
        """
        Parses the LLM output from JSON format into a dictionary of subtasks.
        Strips extra markers like ```json at the start and ``` at the end if present.

        Args:
            decomposition_result (str): The raw LLM output in JSON format.

        Returns:
            dict: A dictionary of subtasks parsed from the LLM output.
        """
        try:
            # Strip markers ```json and ```
            decomposition_result = decomposition_result.strip().strip('```json').strip('```')

            # Parse the cleaned JSON string into a dictionary
            subtasks = json.loads(decomposition_result)
            
            # Ensure the parsed object is a dictionary
            if not isinstance(subtasks, dict):
                raise ValueError("The LLM output is not in the expected dictionary format.")

            logger.info(f"Successfully parsed subtasks: {subtasks}")
            return subtasks
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {str(e)}")
            raise
        except ValueError as ve:
            logger.error(f"Invalid format received: {str(ve)}")
            raise


    def combine_results(self, sub_results: List[Any], subtasks: dict) -> str:
        """
        Combines the results of the subtasks into a structured summary,
        preserving the order of the subtasks.

        Args:
            sub_results (List[Any]): The results of the processed subtasks.
            subtasks (dict): The dictionary of subtasks corresponding to the results.

        Returns:
            str: A structured document summarizing the results of all subtasks.
        """
        document = "Book Analysis Summary:\n\n"
        for idx, (key, task_description) in enumerate(subtasks.items()):
            result = sub_results[idx]
            document += f"## {task_description}\n{result.content}\n\n"
        return document
