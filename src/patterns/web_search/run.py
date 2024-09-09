from src.patterns.web_search.factory import TaskFactory
from src.patterns.web_search.tasks import SummarizeTask, SearchTask, ScrapeTask
from src.patterns.web_search.pipeline import Pipeline
from src.config.logging import logger
from functools import lru_cache
from typing import Optional


class Runner:
    """
    Container class that manages task creation and caching for pipeline execution.
    Uses lru_cache to cache instances of the tasks to improve performance.
    """

    @lru_cache()
    def search_task(self) -> SearchTask:
        """
        Creates and caches the search task.
        
        Returns:
            SearchTask: The search task instance.
        """
        logger.info("Creating search task.")
        return TaskFactory.create_search_task()

    @lru_cache()
    def scrape_task(self) -> ScrapeTask:
        """
        Creates and caches the scrape task.
        
        Returns:
            ScrapeTask: The scrape task instance.
        """
        logger.info("Creating scrape task.")
        return TaskFactory.create_scrape_task()

    @lru_cache()
    def summarize_task(self) -> SummarizeTask:
        """
        Creates and caches the summarize task.
        
        Returns:
            SummarizeTask: The summarize task instance.
        """
        logger.info("Creating summarize task.")
        return TaskFactory.create_summarize_task()

    @lru_cache()
    def pipeline(self) -> Pipeline:
        """
        Creates and caches the pipeline composed of search, scrape, and summarize tasks.
        
        Returns:
            Pipeline: The complete pipeline instance.
        """
        try:
            logger.info("Creating pipeline with search, scrape, and summarize tasks.")
            pipeline = Pipeline(
                self.search_task(),
                self.scrape_task(),
                self.summarize_task()
            )
            return pipeline
        except Exception as e:
            logger.error(f"Failed to create pipeline: {str(e)}")
            raise

    
def run(query: str, model_name: Optional[str] = 'gemini-1.5-flash-001') -> str:
    """
    Main function that initializes the container, constructs the pipeline, and executes it.
    
    Args:
        query (str): The search query to be processed.
        model_name (Optional[str]): The model name used for summarization. Defaults to 'gemini-1.5-flash-001'.
    
    Returns:
        str: The summary result from the pipeline execution.
    
    Raises:
        Exception: If any error occurs during pipeline execution, it is logged and re-raised.
    """
    try:
        logger.info(f"Starting pipeline for query: {query} with model: {model_name}")
        runner = Runner()
        pipeline = runner.pipeline()
        summary = pipeline.run(model_name, query)
        logger.info("Pipeline run successfully completed.")
        return summary
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        raise


if __name__ == '__main__':
    query = 'best hotels in Key West, Florida'
    summary = run(query)
    logger.info(f"Generated Summary: {summary}")

