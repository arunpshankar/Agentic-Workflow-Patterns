from src.config.logging import logger
from src.utils.io import load_yaml
from typing import Union
from typing import Tuple
from typing import Dict 
import requests


class SerpAPIClient:
    """
    A client for interacting with the SERP API for performing search queries.
    """

    def __init__(self, api_key: str):
        """
        Initialize the SerpAPIClient with the provided API key.

        Parameters:
        -----------
        api_key : str
            The API key for authenticating with the SERP API.
        """
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search.json"

    def search(self, query: str, engine: str = "google") -> Union[Dict[str, Any], Tuple[int, str]]:
        """
        Perform a search query using the SERP API.

        Parameters:
        -----------
        query : str
            The search query string.
        engine : str, optional
            The search engine to use (default is "google").

        Returns:
        --------
        Union[Dict[str, Any], Tuple[int, str]]
            The search results as a JSON dictionary if successful, or a tuple containing the HTTP status code
            and error message if the request fails.
        """
        params = {
            "engine": engine,
            "q": query,
            "api_key": self.api_key
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to SERP API failed: {e}")
            return response.status_code, str(e)


def load_api_key(credentials_path: str) -> str:
    """
    Load the API key from the specified YAML file.

    Parameters:
    -----------
    credentials_path : str
        The path to the YAML file containing the API credentials.

    Returns:
    --------
    str
        The API key extracted from the YAML file.

    Raises:
    -------
    KeyError
        If the 'serp' or 'key' keys are missing in the YAML file.
    """
    config = load_yaml(credentials_path)
    return config['serp']['key']


def log_top_search_results(results: Dict[str, Any], top_n: int = 5) -> None:
    """
    Log the top N search results in a formatted manner.

    Parameters:
    -----------
    results : Dict[str, Any]
        The search results returned from the SERP API.
    top_n : int, optional
        The number of top search results to log (default is 5).
    """
    logger.info(f"Top {top_n} Search Results:")
    for i, result in enumerate(results.get('organic_results', [])[:top_n], start=1):
        logger.info(f"Result #{i}:")
        logger.info(f"  Position: {result.get('position')}")
        logger.info(f"  Title: {result.get('title')}")
        logger.info(f"  Link: {result.get('link')}")
        logger.info(f"  Snippet: {result.get('snippet')}")
        logger.info('-' * 100)


def save_top_search_results_to_markdown(results: Dict[str, Any], output_path: str, top_n: int = 5) -> None:
    """
    Save the top N search results to a Markdown file in a formatted manner.

    Parameters:
    -----------
    results : Dict[str, Any]
        The search results returned from the SERP API.
    output_path : str
        The file path where the Markdown file will be saved.
    top_n : int, optional
        The number of top search results to save (default is 5).
    """
    with open(output_path, 'w') as md_file:
        md_file.write(f"# Top {top_n} Search Results\n\n")
        for i, result in enumerate(results.get('organic_results', [])[:top_n], start=1):
            md_file.write(f"## Result #{i}\n")
            md_file.write(f"**Position**: {result.get('position')}\n\n")
            md_file.write(f"**Title**: [{result.get('title')}]({result.get('link')})\n\n")
            md_file.write(f"**Snippet**: {result.get('snippet')}\n\n")
            md_file.write(f"{'-' * 100}\n\n")


def run():
    """
    Main function to execute the Google search using SERP API, log the top results, 
    and save them to a Markdown file.
    """
    credentials_path = './credentials/key.yaml'
    search_query = "perplexity metric"
    markdown_output_path = "./output/top_search_results.md"

    # Load the API key
    api_key = load_api_key(credentials_path)

    # Initialize the SERP API client
    serp_client = SerpAPIClient(api_key)

    # Perform the search
    results = serp_client.search(search_query)

    # Check if the search was successful
    if isinstance(results, dict):
        # Log the top search results
        log_top_search_results(results)

        # Save the top search results to a Markdown file
        save_top_search_results_to_markdown(results, markdown_output_path)
    else:
        # Handle the error response
        status_code, error_message = results
        logger.error(f"Search failed with status code {status_code}: {error_message}")


if __name__ == "__main__":
    run()