import asyncio
from typing import List, Any
from agent import Agent
from src.patterns.dynamic_task_decomposition.delegates import SubTaskAgent
from src.patterns.dynamic_task_decomposition import Message
from src.llm.generate import ResponseGenerator
from src.config.logging import logger

class CoordinatorAgent(Agent):
    """
    An agent that coordinates the processing of a book by decomposing the main task
    into subtasks using an LLM and assigning them to sub-agents to execute in parallel.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        logger.info(f"{self.name} initialized.")

    async def process(self, message: Message) -> Message:
        logger.info(f"{self.name} processing message.")
        try:
            book_content = message.content  # The content of the book

            # Use LLM to decompose the main task into subtasks
            subtasks = await self.decompose_task(book_content)

            # Create sub-agents and execute subtasks in parallel
            tasks = []
            for idx, subtask in enumerate(subtasks):
                agent_name = f"SubTaskAgent_{idx}"
                agent = SubTaskAgent(name=agent_name)
                sub_message = Message(
                    content={"book": book_content, "task": subtask},
                    sender=self.name,
                    recipient=agent_name
                )
                task = asyncio.create_task(agent.process(sub_message))
                tasks.append(task)

            # Gather results from all sub-agents concurrently
            sub_results = await asyncio.gather(*tasks)

            # Combine results into a structured document, preserving order
            combined_result = self.combine_results(sub_results, subtasks)

            # Return the final message
            return Message(content=combined_result, sender=self.name, recipient=message.sender)

        except Exception as e:
            logger.error(f"Error during processing: {str(e)}")
            return Message(
                content="An error occurred while processing the book.",
                sender=self.name,
                recipient=message.sender
            )

    async def decompose_task(self, book_content: str) -> List[str]:
        """
        Uses an LLM to deduce up to 5 independent subtasks from the main task.
        """
        logger.info("Decomposing main task into subtasks using LLM.")

        # Prepare the prompt for the LLM
        llm_input = (
            "You are an expert in literary analysis. Given the text of a book, "
            "generate up to 5 independent analysis tasks that can be executed in parallel. "
            "The tasks should cover different aspects of the book such as characters, plot, themes, etc. "
            "Return the tasks as a numbered list.\n\n"
            "Book Text:\n"
            f"{book_content[:1000]}..."  # Limiting the text sent to the LLM for brevity
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

            # Parse the decomposition result into a list of subtasks
            subtasks = self.parse_subtasks(decomposition_result)

            logger.info(f"Subtasks generated by LLM: {subtasks}")

            return subtasks

        except Exception as e:
            logger.error(f"Failed to decompose task: {str(e)}")
            raise

    def parse_subtasks(self, decomposition_result: str) -> List[str]:
        """
        Parses the LLM output into a list of subtasks.
        """
        # Simple parsing assuming the LLM returns a numbered list
        lines = decomposition_result.strip().split('\n')
        subtasks = []
        for line in lines:
            if line.strip():
                # Remove numbering if present
                subtask = line.strip().lstrip('0123456789. ').strip()
                subtasks.append(subtask)
        return subtasks

    def combine_results(self, sub_results: List[Any], subtasks: List[str]) -> str:
        """
        Combines the results of the subtasks into a structured summary,
        preserving the order of subtasks.
        """
        document = "Book Analysis Summary:\n\n"
        for idx, result in enumerate(sub_results):
            section_title = subtasks[idx]
            document += f"## {section_title}\n{result.content}\n\n"
        return document
