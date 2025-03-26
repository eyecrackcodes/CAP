# RPL (Revenue Per Lead) Tracker

A web application for tracking and analyzing Revenue Per Lead (RPL) metrics over time. This application helps you monitor the revenue generation of your leads by calculating RPL based on the total premium from placed deals.

## Features

- Daily data entry for leads and premiums
- Interactive charts showing RPL trends
- Summary statistics for selected date ranges
- Detailed data table view
- Responsive design for desktop and mobile use

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd rpl-tracker
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Use the navigation menu to:
   - Add daily data (leads and premiums)
   - View reports with charts and statistics
   - Analyze RPL trends over time

## RPL Calculation

The application calculates RPL using the following formula:

```
RPL = Total Premium / Number of Leads

Where:
- Total Premium: Revenue from placed deals
- Number of Leads: Total number of leads generated
```

## Development

- Built with Flask (Python web framework)
- Uses SQLite for data storage
- Frontend built with Bootstrap 5
- Charts created using Plotly.js
- jQuery for AJAX requests and DOM manipulation

## License

This project is licensed under the MIT License - see the LICENSE file for details. 