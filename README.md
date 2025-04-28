# Crawl4AI Web Crawler and Processor

A powerful web crawling and content processing tool built with the Crawl4AI library, designed for efficient web scraping and markdown content generation.

## Features

- **Deep Web Crawling**: Crawl websites to configurable depths with customizable parameters
- **Intelligent Page Prioritization**: Prioritize pages based on keyword relevance
- **Multiple Output Formats**:
  - `json`: Save crawled URLs to JSON file
  - `md`: Generate full markdown files from crawled pages
  - `md-fit`: Generate optimized markdown content
- **Domain Filtering**: Option to include or exclude external domains
- **Interactive Mode**: User-friendly configuration through interactive prompts
- **Flexible Processing**: Process previously crawled results without re-crawling

## Requirements

- Python 3.6+
- Dependencies (specified in `requirements.txt`):
  - crawl4ai >= 0.6.0
  - aiohttp >= 3.8.0
  - lxml >= 4.9.0

## Installation

1. Clone this repository or download the script
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the script with default settings in interactive mode:

```bash
python deep_crawler.py
```

### Command Line Arguments

Run with specific parameters:

```bash
python deep_crawler.py --url https://docs.example.com --max-depth 3 --max-pages 100
```

### Available Options

| Option | Description |
|--------|-------------|
| `-i, --interactive` | Run in interactive mode with prompts |
| `--mode {crawl,process,both}` | Operation mode (default: both) |
| `--url, -u` | Starting URL for crawling |
| `--max-depth, -d` | Maximum crawl depth (default: 2) |
| `--max-pages, -p` | Maximum pages to crawl (default: 50) |
| `--keywords, -k` | Keywords to prioritize during crawling |
| `--include-external` | Include links to external domains |
| `--output, -o` | Output format: json, md, or md-fit (default: md-fit) |
| `--results-file` | Path to existing results JSON file to process |

### Operation Modes

- **crawl**: Only crawl and save results to JSON
- **process**: Process an existing results.json file (no crawling)
- **both**: Crawl and then process the results (default)

### Examples

Crawl a website with keyword prioritization:

```bash
python deep_crawler.py -u https://docs.example.com -d 3 -p 100 -k blockchain defi web3
```

Process existing results:

```bash
python deep_crawler.py --mode process --results-file results.json
```

## Output

- **results.json**: Contains structured data about crawled pages
- **markdown_output/**: Generated markdown files organized by domain
  - Format: `markdown_output/domain.com/path_to_page.md`

## How It Works

1. **Crawling**: The script uses BestFirstCrawlingStrategy to intelligently explore the website, prioritizing pages based on relevance to specified keywords
2. **Results Storage**: Crawled URLs are saved to a JSON file with metadata
3. **Content Processing**: Pages are processed into markdown files using the 'crwl' command
4. **Organization**: Output files are organized in folders based on the domain name

## License

[Specify your license here]

## Contributors

[Your name/organization]