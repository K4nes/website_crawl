#!/usr/bin/env python3
"""
Crawl4AI Web Crawler and Processor

This script performs:
1. Deep web crawling using Crawl4AI with configurable parameters:
   - URL: The starting point for crawling
   - Max Depth: How many levels deep to crawl
   - Max Pages: Maximum number of pages to crawl
2. Processing of crawled URLs to generate markdown content

Simply run: python3 deep_crawler.py
"""

import asyncio
import argparse
import json
import os
import subprocess
import sys
from typing import List, Dict, Any
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer


# Default values (hardcoded as requested)
DEFAULT_DELAY = 0.5
DEFAULT_CONCURRENCY = 5
DEFAULT_OUTPUT_FILE = "results.json"
DEFAULT_MARKDOWN_DIR = "markdown_output"
DEFAULT_OVERWRITE = False
DEFAULT_VERBOSE = 0


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Deep web crawler and content processor using Crawl4AI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Interactive mode flag
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode with prompts for options"
    )
    
    # Add a mode selection option
    parser.add_argument(
        "--mode",
        choices=["crawl", "process", "both"],
        default="both",
        help="Operation mode: crawl (crawl only), process (process existing results.json), both (crawl and process)"
    )
    
    # Add option to process existing results file
    parser.add_argument(
        "--results-file",
        default=DEFAULT_OUTPUT_FILE,
        help="Path to existing results JSON file to process (for process mode)"
    )
    
    # Required inputs
    parser.add_argument(
        "--url", "-u", 
        help="Starting URL for crawling"
    )
    parser.add_argument(
        "--max-depth", "-d", 
        type=int, 
        default=2, 
        help="Maximum levels to crawl from the starting URL"
    )
    parser.add_argument(
        "--max-pages", "-p", 
        type=int, 
        default=50, 
        help="Maximum pages to crawl"
    )
    
    # Optional inputs
    parser.add_argument(
        "--keywords", "-k", 
        nargs="+", 
        default=[], 
        metavar="KEYWORD",
        help="Keywords to prioritize during crawling (space-separated)"
    )
    parser.add_argument(
        "--include-external", 
        action="store_true", 
        help="Include links to external domains (by default only crawls within the same domain)"
    )
    
    # Output format - simplified
    parser.add_argument(
        "--output", "-o", 
        choices=["json", "md", "md-fit"],
        default="md-fit", 
        help="Output format: json (data only), md (full markdown), md-fit (optimized markdown)"
    )
    
    return parser.parse_args()


def prompt_for_input(prompt_text, default=None, validator=None):
    """Prompt user for input with optional default value and validation."""
    default_display = f" [{default}]" if default is not None else ""
    while True:
        user_input = input(f"{prompt_text}{default_display}: ")
        
        # Use default if user just presses Enter
        if not user_input and default is not None:
            return default
        
        # Validate input if validator provided
        if validator and user_input:
            try:
                result = validator(user_input)
                return result
            except ValueError as e:
                print(f"Invalid input: {e}")
                continue
        
        if user_input:  # Don't accept empty input if no default
            return user_input
        
        print("Input required. Please try again.")


def prompt_for_url():
    """Prompt user for a URL."""
    return prompt_for_input("Enter starting URL", "https://docs.example.com")


def prompt_for_int(prompt_text, default):
    """Prompt user for an integer value."""
    def validate_int(val):
        try:
            result = int(val)
            if result < 0:
                raise ValueError("Value must be positive")
            return result
        except ValueError:
            raise ValueError("Please enter a valid positive number")
    
    return prompt_for_input(prompt_text, default, validate_int)


def prompt_for_yes_no(prompt_text, default=False):
    """Prompt user for a yes/no response."""
    default_str = "y" if default else "n"
    response = prompt_for_input(f"{prompt_text} (y/n)", default_str)
    return response.lower().startswith('y')


def prompt_for_options(prompt_text, options, default=None):
    """Prompt user to select from a list of options."""
    if not options:
        raise ValueError("No options provided")
    
    # Show options to user
    print(f"\n{prompt_text}")
    for i, option in enumerate(options):
        print(f"  {i+1}. {option}")
    
    # Determine default index
    default_index = None
    if default in options:
        default_index = options.index(default) + 1
    
    # Get selection
    while True:
        if default_index:
            selection = input(f"Enter selection [1-{len(options)}] [{default_index}]: ")
            if not selection:
                return options[default_index - 1]
        else:
            selection = input(f"Enter selection [1-{len(options)}]: ")
        
        try:
            if selection:
                index = int(selection) - 1
                if 0 <= index < len(options):
                    return options[index]
                print(f"Please enter a number between 1 and {len(options)}")
            elif not default_index:
                print("Input required. Please try again.")
        except ValueError:
            print("Please enter a valid number")


def get_interactive_arguments(args):
    """Interactively prompt for required arguments."""
    print("\n=== Crawl4AI Interactive Configuration ===\n")
    
    # Always prompt for required parameters
    args.url = prompt_for_url()
    args.max_depth = prompt_for_int("Maximum crawl depth", args.max_depth or 2)
    args.max_pages = prompt_for_int("Maximum pages to crawl", args.max_pages or 50)
    
    # Keywords handling
    keywords_default = ""
    if args.keywords and len(args.keywords) > 0:
        keywords_default = ", ".join(args.keywords)
        
    keywords_input = prompt_for_input(
        "Keywords to prioritize (comma-separated, leave empty for none)", 
        keywords_default
    )
    
    if keywords_input:
        args.keywords = [k.strip() for k in keywords_input.split(',')]
    else:
        args.keywords = []
        
    # Include external domains
    args.include_external = prompt_for_yes_no(
        "Include external domains?", 
        args.include_external
    )
    
    # Output format with better explanations
    print("\nSelect output format:")
    print("  1. json    - Only save URLs to results.json without processing")
    print("  2. md      - Process URLs from results.json into full markdown")
    print("  3. md-fit  - Process URLs from results.json into optimized markdown")
    
    # Determine default index
    options = ["json", "md", "md-fit"]
    default = args.output or "md-fit"
    default_index = options.index(default) + 1
    
    # Get selection
    while True:
        selection = input(f"Enter selection [{default_index}]: ")
        
        if not selection:
            args.output = options[default_index - 1]
            break
            
        try:
            if selection:
                index = int(selection) - 1
                if 0 <= index < len(options):
                    args.output = options[index]
                    break
                print("Please enter a number between 1 and 3")
        except ValueError:
            print("Please enter a valid number")
    
    print("\nConfiguration complete. Starting process...\n")
    return args


async def run_crawler(
    url: str, 
    max_depth: int, 
    max_pages: int, 
    include_external: bool = False, 
    keywords: List[str] = None,
    user_agent: str = "Crawl4AI/1.0",
    verbose: int = DEFAULT_VERBOSE
) -> List[Dict[str, Any]]:
    """Run the deep crawler with specified parameters."""
    # Configure crawler strategy
    url_scorer = None
    if keywords and len(keywords) > 0:
        url_scorer = KeywordRelevanceScorer(
            keywords=keywords,
            weight=0.7  # Default weight for keyword relevance
        )
    
    strategy = BestFirstCrawlingStrategy(
        max_depth=max_depth,
        include_external=include_external,
        max_pages=max_pages,
        url_scorer=url_scorer
    )
    
    # Configure the crawler - using only parameters supported by CrawlerRunConfig
    config = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=verbose > 0
    )
    
    # Run the crawler
    async with AsyncWebCrawler() as crawler:
        if verbose > 0:
            print(f"Starting crawler with config: {config}")
        
        results = await crawler.arun(url, config=config)
        
        # Process the results to make them JSON serializable
        processed_results = []
        for result in results:
            processed_result = {
                "url": result.url,
                "depth": result.metadata.get("depth", 0),
                "title": result.metadata.get("title", ""),
            }
            processed_results.append(processed_result)
            
        return processed_results


def save_results(results: List[Dict[str, Any]], output_file: str = DEFAULT_OUTPUT_FILE):
    """Save the crawl results to a JSON file."""
    output_path = Path(output_file)
    
    # Create directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {output_path.absolute()}")
    return output_path


def process_urls(
    results_file: str, 
    source_url: str = None, 
    output_format: str = "md-fit", 
    markdown_dir: str = DEFAULT_MARKDOWN_DIR,
):
    """
    Process URLs and generate output based on the selected format using crwl command.
    
    Args:
        results_file: Path to the JSON file with crawl results
        source_url: The original URL that was crawled (used for folder naming)
        output_format: Format for markdown output (json, md, md-fit)
        markdown_dir: Base directory for markdown output
    """
    # Load URLs from results json file
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Create domain-based subfolder from source URL
    domain = None
    if source_url:
        parsed_source = urlparse(source_url)
        domain = parsed_source.netloc.replace("www.", "").split(':')[0]
    
    # If we couldn't get domain from source_url, try to get from first result
    if not domain and results:
        first_url = results[0]['url']
        parsed_first = urlparse(first_url)
        domain = parsed_first.netloc.replace("www.", "").split(':')[0]
    
    # Create output directory structure
    output_dir = Path(markdown_dir)
    if domain:
        output_dir = output_dir / domain
    
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"Found {len(results)} URLs to process")
    print(f"Output directory: {output_dir}")
    
    processed_count = 0
    error_count = 0
    
    # Process each URL
    for i, result in enumerate(results):
        url = result['url']
        parsed_url = urlparse(url)
        
        # Create a slug for the filename
        path = parsed_url.path.strip('/')
        if path:
            # Replace slashes with underscores for a valid filename
            slug = path.replace('/', '_')
        else:
            # If path is empty, use index
            slug = "index"
        
        # Clean up the slug
        slug = slug.split('.')[0]  # Remove file extensions like .html
        filename = f"{slug}.md"
        
        output_path = output_dir / filename
        
        print(f"Processing {i+1}/{len(results)}: {url}")
        
        # Build the crwl crawl command with all available options
        cmd = [
            "crwl", "crawl",
            url,
            "-o", output_format,   # Output format (json, md, md-fit)
            "-O", str(output_path)  # Output file path
        ]
        
        # Run the command
        try:
            subprocess.run(cmd, check=True)
            processed_count += 1
            print(f"  ✓ Created {output_path}")
        except subprocess.CalledProcessError as e:
            error_count += 1
            print(f"  ✗ Error processing {url}: {e}")
        except Exception as e:
            error_count += 1
            print(f"  ✗ Unexpected error: {e}")
    
    # Summary
    print(f"\nProcessing complete: {processed_count} created, {error_count} errors")


async def main():
    """Main function that combines crawl and process functionality."""
    args = parse_arguments()
    
    # Check if we need interactive mode
    if not sys.argv[1:] or args.interactive:  # If no command line args or explicit interactive
        args.interactive = True
        args = get_interactive_arguments(args)
    
    # Process-only mode
    if args.mode == "process":
        print(f"Processing existing results from: {args.results_file}")
        if not os.path.exists(args.results_file):
            print(f"Error: Results file not found: {args.results_file}")
            return
            
        try:
            # Call process_urls directly with the existing results file
            process_urls(
                results_file=args.results_file,
                source_url=args.url,  # Optional, may be None
                output_format=args.output,
                markdown_dir=DEFAULT_MARKDOWN_DIR
            )
            print("\nCrawl4AI processing completed successfully!")
            return
        except Exception as e:
            print(f"Error during processing: {e}")
            return
    
    # Validate arguments for crawl mode
    if args.mode in ["crawl", "both"] and not args.url:
        print("Error: URL is required for crawling. Please provide a starting URL.")
        return
    
    # Crawl mode
    if args.mode in ["crawl", "both"]:
        print(f"Starting deep crawl of {args.url}")
        print(f"Max depth: {args.max_depth}, Max pages: {args.max_pages}")
        
        try:
            # Step 1: Run the crawler
            results = await run_crawler(
                url=args.url,
                max_depth=args.max_depth,
                max_pages=args.max_pages,
                include_external=args.include_external,
                keywords=args.keywords,
                verbose=DEFAULT_VERBOSE
            )
            
            print(f"Crawled {len(results)} pages")
            
            # Step 2: Save results to JSON file
            results_file = save_results(results, args.results_file)
            
            # Step 3: Process results if in "both" mode
            if args.mode == "both" and args.output != "json":
                print(f"Processing URLs to {args.output} format...")
                process_urls(
                    results_file=args.results_file,
                    source_url=args.url,
                    output_format=args.output,
                    markdown_dir=DEFAULT_MARKDOWN_DIR
                )
                
        except Exception as e:
            print(f"Error during processing: {e}")
            return
            
    print("\nCrawl4AI process completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())