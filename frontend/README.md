# Roshtaty – Prescription Reader

Roshtaty is a web application I built to make reading medical prescriptions easier. It takes an image of a printed or handwritten prescription, extracts the text, and organizes the information into a medicine list that is easier to read.

The goal is to reduce the time spent reading prescription details and make the extracted information easier to review. Since handwriting and image quality can affect the results, the original prescription should always be checked before relying on the extracted information.

## What the Project Can Do

- **Upload prescriptions:** Select an image or drag and drop it into the application. Supported formats include JPG, PNG, WEBP, BMP, and TIFF, with a maximum file size of 10 MB.
- **Extract text from images:** OpenCV prepares the image for reading, and Tesseract OCR extracts the text. The application tries different image-processing approaches to improve the result.
- **Organize medicine details:** The parser identifies available information such as medicine name, strength, dosage form, dose, frequency, duration, and additional instructions.
- **Read patient information:** When available and readable, the application can extract details such as the patient's name, age, prescription date, and doctor's name.
- **Review scan results:** Each scan includes information such as OCR confidence, word count, number of medicines, and processing time.
- **Export results:** Copy the extracted summary or download it as a text file or CSV spreadsheet.
- **View recent scans:** The browser keeps a history of the last six scans, including thumbnails.
- **Try sample prescriptions:** Two sample prescriptions are included to help users explore the application without uploading their own images.

## Screenshots

The screenshots below show the application and some of its main features.

### Main Results Workspace

![Prescription results workspace](screenshots/03b-results-workspace.png)

### Uploading a Prescription

![Prescription upload screen](screenshots/02-upload-selected.png)

### Scan History

![Prescription scan history](screenshots/05-history.png)

More screenshots are available in the [`screenshots`](screenshots/) folder.

## Technologies Used

- **Python** – backend logic and prescription processing
- **Flask** – web server and API endpoints
- **OpenCV** – image preprocessing
- **Tesseract OCR** – text extraction from prescription images
- **HTML, CSS, and JavaScript** – frontend interface
- **SQLite** – local database support in the project

## Project Structure

```text
Roshtaty-Prescription-reader/
├── backend/
│   ├── api/
│   │   └── v1/
│   │       └── routes/
│   │           ├── __init__.py
│   │           ├── medicines.py
│   │           └── safety.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── data/
│   │   └── roshtaty.db
│   ├── models/
│   │   └── medicine.py
│   ├── services/
│   │   ├── ingestion/
│   │   └── safety/
│   ├── tools/
│   ├── app.py
│   ├── init_db.py
│   ├── ocr.py
│   ├── parser.py
│   └── requirements.txt
├── frontend/
│   ├── assets/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── screenshots/
├── tools/
├── .gitignore
├── README.md
└── start.bat
```

## Getting Started

### Requirements

Before running the application, make sure you have:

- Python 3.10 or later
- Tesseract OCR 5.x
- The Python packages listed in `backend/requirements.txt`

On Windows, Tesseract can be installed using the [UB Mannheim Windows installer](https://github.com/UB-Mannheim/tesseract/wiki).

### Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/kerolosmichelle/Roshtaty-Prescription-reader.git
cd Roshtaty-Prescription-reader
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the required Python packages:

```bash
python -m pip install -r backend/requirements.txt
```

If PowerShell does not allow the activation script to run, you can install the packages using `.venv\Scripts\python.exe` instead.

### Configure Tesseract

Make sure Tesseract is installed and accessible to the application. If it is not available through your system PATH, configure the executable path using the `TESSERACT_CMD` environment variable, if supported by the current configuration.

The OCR language defaults to English. Arabic recognition requires the appropriate Arabic language data to be installed and configured.

### Run the Application

Start the Flask application:

```bash
python backend/app.py
```

If the application starts successfully, open the local address configured by Flask in your browser. The default address for the original application is:

http://127.0.0.1:5000

The actual startup command and address may depend on the current backend configuration.

## API

The original prescription-reading interface uses a POST endpoint to submit an image for text extraction. The project also contains versioned API routes for medicine-related and safety-related functionality.

### Prescription Extraction

The original interface uses:

`POST /extract-text`

The endpoint also supports the alias:

`POST /api/extract`

The request uses `multipart/form-data` with an image field.

A successful response can contain:

- Extracted text
- OCR confidence and word count
- Detected medicines and their available details
- Patient information, when readable
- Processing time

The exact response fields depend on the active backend implementation.

### Health Check

The original application also defines:

`GET /api/health`

This endpoint reports service information such as status and OCR configuration.

## Privacy and Data Handling

Prescription images may contain sensitive personal information. The original OCR workflow is designed to remove uploaded images from its temporary upload directory after processing.

However, this should not be treated as a guarantee that every part of the current application is automatically private. Database records, browser history, server logs, and deployment settings must also be reviewed before using real patient information.

For testing and demonstrations, use sample or appropriately anonymized prescriptions.

## Limitations

Handwritten prescriptions can be difficult to read, and OCR may misinterpret medicine names, strengths, or dosage instructions. Extracted information may also be incomplete or incorrectly categorized.

Roshtaty is a prescription-reading and information-organizing tool. It does not diagnose medical conditions, prescribe medicines, or replace a doctor's or pharmacist's judgment.

**Always compare the extracted information with the original prescription and ask a qualified healthcare professional to clarify anything uncertain.**

## About the Project

I developed Roshtaty to explore how image processing and OCR can be used to make prescription information easier to read and organize. Building it involved working with a Python backend, a browser-based interface, image preprocessing, and text parsing.

The project is a work in progress, and I plan to continue improving its accuracy, reliability, and usability.

## License

No license has been specified yet. Please check the repository's licensing terms before reusing or distributing this project.
