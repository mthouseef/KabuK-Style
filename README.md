# KabuK-Style

KabuK-Style is a data extraction project designed to scrape and process data from the website [Jalan.net](https://www.jalan.net/). This project focuses on extracting various types of information from the website to facilitate data analysis and reporting.

## Features

- **Data Extraction**: Extracts detailed information from Jalan.net, including hotel listings, and pricing.
- **Data Processing**: Processes the extracted data and formats it for analysis.
- **Output Formats**: Supports saving data in csv formats.

## Requirements

- Python 3.x
- Required Python libraries:
  - `requests`
  - `lxml`
  - `pandas`
  - `chardet` (for encoding file handling)

You can install the required libraries using pip:

```bash
pip install -r requirements.txt



Setup
Clone the Repository

bash
Copy code
git clone https://github.com/mthouseef/KabuK-Style.git
cd KabuK-Style
Install Dependencies

bash
Copy code
pip install -r requirements.txt
Usage
Configure the Scraper

Run the Scraper

Execute the main script to start the data extraction process:

bash
Copy code
python jalan.py
The data will be extracted and saved in the specified format.

File Structure
jalan.py: The main script to run the data extraction.
requirements.txt: List of required Python libraries.
