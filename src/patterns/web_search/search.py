from vertexai.preview.generative_models import FunctionDeclaration
from vertexai.preview.generative_models import GenerationResponse
from src.patterns.web_search.utils import generate_filename
from vertexai.preview.generative_models import Tool
from src.patterns.web_search.tasks import SearchTask
from src.llm.generate import ResponseGenerator
from src.prompt.manage import TemplateManager
from src.config.logging import logger
from typing import Optional
from typing import Dict 
from typing import Any 
import json
import os 


class WebSearchAgent(SearchTask):
    """
    WebSearchAgent is responsible for orchestrating search operations using a
    language model, generating instructions, and performing the search.

    Attributes:
        TEMPLATE_PATH (str): The path to the template configuration file used for search.
        response_generator (ResponseGenerator): Instance to generate responses from the LLM.
        template_manager (TemplateManager): Instance to manage and fill templates for search instructions.
    """
    TEMPLATE_PATH = './config/patterns/web_search.yml'

    def __init__(self) -> None:
        """
        Initializes WebSearchAgent with the response generator and template manager.
        """
        self.response_generator = ResponseGenerator()
        self.template_manager = TemplateManager(self.TEMPLATE_PATH)

    def create_search_function_declaration(self) -> FunctionDeclaration:
        """
        Creates a function declaration for the web search tool.

        Returns:
            FunctionDeclaration: The function declaration for the web search, describing the parameters and usage.
        """
        return FunctionDeclaration(
            name="web_search",
            description="Perform Google Search using SERP API",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "location": {"type": "string", "description": "Geographic location for localized search results", "default": ""},
                },
                "required": ["query"]
            },
        )

    def function_call(self, model_name: str, search_query: str, search_tool: Tool) -> GenerationResponse:
        """
        Generates a response for the given search query using the provided model and tool.

        Args:
            model_name (str): The name of the model to generate the response.
            search_query (str): The search query string.
            search_tool (Tool): The tool containing the function declaration for search.

        Returns:
            GenerationResponse: The response generated by the language model.

        Raises:
            Exception: If there is an error during the response generation.
        """
        try:
            template = self.template_manager.create_template('tools', 'search')
            system_instruction = template['system']
            user_instruction = self.template_manager.fill_template(template['user'], query=search_query)
            
            logger.info(f"Generating response for search query: {search_query}")
            return self.response_generator.generate_response(
                model_name, 
                system_instruction, 
                [user_instruction], 
                tools=[search_tool]
            )
        except Exception as e:
            logger.error(f"Error generating search data: {e}")
            raise

    def extract_function_args(self, response: GenerationResponse) -> Optional[Dict[str, Any]]:
        """
        Extracts the function arguments from the language model response.

        Args:
            response (GenerationResponse): The response from the language model.

        Returns:
            Optional[Dict[str, Any]]: A dictionary of function arguments, or None if extraction fails.

        Raises:
            Exception: If there is an error during argument extraction.
        """
        try:
            first_candidate = response.candidates[0]
            first_part = first_candidate.content.parts[0]
            function_call = first_part.function_call
            logger.info("Extracting function arguments from the response.")
            return dict(function_call.args) if function_call else None
        except (IndexError, KeyError) as e:
            logger.error(f"Failed to extract function arguments: {e}")
            return None

    def run(self, model_name: str, query: str, location: str = '') -> None:
        try:
            search_tool = Tool(function_declarations=[self.create_search_function_declaration()])
            response = self.function_call(model_name, query, search_tool)
            function_args = self.extract_function_args(response)
            
            if function_args:
                search_query = function_args.get('query', query)
                search_location = location or function_args.get('location', '')
            else:
                search_query = query
                search_location = location

            logger.info(f"Running web search for query: {search_query}, location: {search_location}")
            from src.patterns.web_search.serp import run
            results = run(search_query, search_location)

            # Save results with the new filename format
            filename = generate_filename(search_query)
            output_path = os.path.join("./data/patterns/web_search/output/search", filename)
            with open(output_path, 'w') as f:
                json.dump(results, f)

        except Exception as e:
            logger.error(f"Error during search execution: {e}")
            raise
