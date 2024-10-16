from src.patterns.web_search.tasks import SummarizeTask
from src.llm.generate import ResponseGenerator
from src.prompt.manage import TemplateManager
from src.config.logging import logger
from src.utils.io import read_file
from typing import Dict
import os


class WebContentSummarizeAgent(SummarizeTask):
    """
    WebContentSummarizeAgent is responsible for summarizing scraped web content
    using a language model and predefined templates.
    
    Attributes:
        INPUT_DATA_PATH (str): Path to the file containing scraped content to be summarized.
        OUTPUT_PATH (str): Path to the file where the generated summary will be saved.
        TEMPLATE_PATH (str): Path to the template configuration file for generating instructions.
    """
    INPUT_DATA_PATH = './data/patterns/web_search/output/scrape/scraped_content.txt'
    OUTPUT_PATH = './data/patterns/web_search/output/summarize/summary.txt'
    TEMPLATE_PATH = './config/patterns/web_search.yml'

    def __init__(self) -> None:
        """
        Initializes WebContentSummarizeAgent with a template manager and response generator.
        Reads the HTML content to be summarized during initialization.
        """
        self.template_manager = TemplateManager(self.TEMPLATE_PATH)
        self.response_generator = ResponseGenerator()
        self.html_content = self._read_html_content()

    def _read_html_content(self) -> str:
        """
        Reads the scraped HTML content from the input data path.
        
        Returns:
            str: The HTML content as a string.
        
        Raises:
            Exception: If an error occurs while reading the file.
        """
        try:
            logger.info(f"Reading HTML content from {self.INPUT_DATA_PATH}")
            return read_file(self.INPUT_DATA_PATH)
        except Exception as e:
            logger.error(f"Error reading HTML content: {e}")
            raise

    def run(self, model_name: str, query: str) -> str:
        """
        Runs the summarization process, generating a summary of the scraped content
        using the provided language model, and saves the summary to a file.

        Args:
            model_name (str): The name of the model to be used for summarization.
            query (str): The query used to contextualize the summary.
        
        Raises:
            Exception: If an error occurs during response generation, processing, or saving.
        """
        try:
            # Fetching and processing the template
            logger.info("Fetching and processing template for response generation.")
            template: Dict[str, str] = self.template_manager.create_template('tools', 'summarize')
            
            system_instruction: str = template['system']
            user_instruction: str = self.template_manager.fill_template(
                template['user'], query=query, html_content=self.html_content
            )

            print('LLL', user_instruction)
            
            # Generating the response
            logger.info("Generating response from LLM...")
            response = self.response_generator.generate_response(
                model_name, system_instruction, [user_instruction]
            )
            #print('>>>>', response)
            summary: str = response.text.strip()
            #print('==', summary)
            
            logger.info("Response generated successfully.")
            
            # Save the summary
            self._save(summary)
            return summary
            
        except Exception as e:
            logger.error(f"Error during summarization process: {e}")
            raise

    def _save(self, summary: str) -> None:
        """
        Saves the generated summary to a text file.

        Args:
            summary (str): The generated summary to be saved.

        Raises:
            Exception: If an error occurs while saving the summary.
        """
        try:
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(self.OUTPUT_PATH), exist_ok=True)

            logger.info(f"Saving summary to {self.OUTPUT_PATH}")
            
            with open(self.OUTPUT_PATH, 'w', encoding='utf-8') as file:
                file.write(summary)
            
            logger.info("Summary saved successfully as a text file.")
        except Exception as e:
            logger.error(f"Error saving summary: {e}")
            raise