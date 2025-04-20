# Nav Assist — Intelligent Website Analysis Agent

Nav Assist is a Streamlit-based web assistant that leverages OpenAI and LangSmith to automate website analysis, navigation, and content mapping. It allows users to analyze a site structure, interact via AI-powered queries, and track metrics using LangSmith.

## Features

- Website Sitemap Extraction  
  Extracts navigation, content sections, forms, and social links from any website.

- AI-Powered Agent  
  Uses OpenAI (gpt-4o) with Browser-Use to intelligently navigate and extract relevant information.

- Metrics Dashboard  
  LangSmith integration for monitoring agent performance, latency, and token usage.

- Prompt Security  
  Enhanced system prompts and validation against prompt injection and external abuse.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/nav-assist-agent.git
cd nav-assist-agent
```

### 2. Install Poetry

If you don’t have Poetry installed:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. Install Dependencies

```bash
poetry install
```

### 4. Set Up Environment Variables

Create a `.env` file in the root directory with the following:

```env
OPENAI_API_KEY=your-openai-key
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=nav-assist
```

> Alternatively, use `streamlit secrets` or set env vars directly in your shell.

## Running the App

```bash
poetry run streamlit run main.py
```

The app will launch at http://localhost:8501

## Project Structure

```plaintext
nav-assist-agent/
│
├── main.py                           # Streamlit app entry point
├── services/
│   ├── config.py                     # Session state, env loader, key validation
│   ├── agent_service.py              # Browser agent runner with LangChain + browser-use
│   ├── sitemap_service.py           # WebsiteSitemapExtractor logic
│   ├── prompt_service.py            # Dynamic prompt generation
│   ├── langsmith_config.py          # LangSmith tracking, setup and metrics
│
├── components/
│   ├── chat_interface.py            # Chat UI
│   ├── sidebar.py                   # Sidebar configuration
│   ├── url_input.py                 # Website URL input & validation
│   ├── analysis_display.py         # Displays overview, content, nav, links, etc.
│   ├── metrics_dashboard.py         # LangSmith dashboard with visual metrics
│
├── .env                             # Your local API keys (not committed)
├── pyproject.toml                   # Poetry dependency manager
```

## API Keys

The following API keys are required:

| Service     | Environment Variable     | Usage                          |
|-------------|--------------------------|---------------------------------|
| OpenAI      | `OPENAI_API_KEY`         | For agent intelligence (ChatOpenAI) |
| LangSmith   | `LANGSMITH_API_KEY`      | For metrics and prompt tracking |
| LangSmith   | `LANGSMITH_PROJECT`      | Project name for analytics     |

You can load them via `.env`, environment, or Streamlit secrets.

## Function Reference

### main.py
- `main()` – Launches Streamlit app with page config, session state, and error handling.

### services/config.py
- `set_page_config()` – Sets up Streamlit UI configuration.
- `validate_key()` – Checks validity of API keys.
- `load_key()` – Loads API key from env or secrets.
- `load_api_key()` – Loads OpenAI API key.
- `load_langsmith_key()` – Loads LangSmith API key.
- `initialize_session_state()` – Initializes all necessary session state defaults.

### services/agent_service.py
- `run_agent_task()` – Runs a task using the browser-use agent with LLM control.
- `_create_enhanced_system_prompt()` – Adds security and formatting to agent system prompt.
- `_process_agent_history()` – Formats the history from browser-use into a user-readable summary.
- `get_agent_status()` – Returns the current status of agent readiness and environment.

### services/sitemap_service.py
- `WebsiteSitemapExtractor` – Class to crawl and extract the website structure.
- `extract_sitemap()` – Extracts initial site data and starts background mapping.
- `start_site_mapping()` – Launches background crawl in a thread.
- `fetch_website_content()` – Fetches HTML with caching and rate-limiting.
- `extract_site_structure()` – Parses HTML to extract structure (nav, content, forms, etc.).
- `find_relevant_pages()` – Finds relevant pages using keyword overlap.
- `generate_report()` – Builds a structured analytics report of the website.
- `export_sitemap_xml()` – Generates a sitemap.xml file from crawl.
- `generate_sitemap()` – Public function adapter for extractor with Streamlit integration.

### services/langsmith_config.py
- `setup_langsmith()` – Initializes LangSmith client.
- `track_prompt()` – Tracks a prompt + result in LangSmith.
- `get_project_metrics()` – Gathers LangSmith analytics over time.

### services/prompt_service.py
- `generate_system_prompt()` – Creates a prompt from site structure for the agent.
- `generate_website_analyzed_message()` – Generates summary after analysis.

### components/url_input.py
- `normalize_url()` – Adds https:// and trims.
- `is_valid_url()` – Validates a URL string.
- `render_url_input()` – Streamlit input form for entering a website URL.

### components/chat_interface.py
- `render_chat_interface()` – Core interaction logic for running the assistant.

### components/analysis_display.py
- `display_sitemap()` – Renders all tabs (Overview, Content, Forms, etc.) in Streamlit.
- `render_overview()` – Displays key metrics and mapping status.
- `render_navigation()` – Shows nav links grouped by section.
- `render_content()` – Lets user view extracted content sections.
- `render_link_analysis()` – Visual breakdown of links by depth and type.
- `render_forms()` – Lists form fields and purpose.
- `render_social()` – Renders grouped social links.

### components/sidebar.py
- `render_sidebar()` – Manages sidebar with toggles, settings, and user inputs.

### components/metrics_dashboard.py
- `render_metrics_dashboard()` – Shows LangSmith project metrics across time.
- `_process_runs_data()` – Normalizes LangSmith data for dashboard rendering.
