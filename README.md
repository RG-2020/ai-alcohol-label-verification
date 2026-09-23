# LabelGuard AI

**Alcohol Label Verification Prototype by Rahel S. Gizaw**

## Live Demo

**Application:** https://labelguard-ai-k2f2.onrender.com

**Source Code:** https://github.com/RG-2020/ai-alcohol-label-verification

LabelGuard AI is a standalone prototype that scans alcohol label images and compares the extracted text against application information. It is designed to support a human reviewer by identifying clear matches, potential mismatches, and fields that need manual review.

The system uses local OCR and deterministic verification rules so uncertain OCR is not treated as a confirmed compliance decision.

Features

Verify Against Application

The reviewer can enter application information and upload front and optional back label images.

LabelGuard AI checks:

Brand name

Class / type

Alcohol content (ABV)

Net contents

Producer / bottler name

Producer / bottler address or country of origin

Government warning

Each field returns one of these results:

MATCH

MISMATCH

REVIEW

The overall result can be:

PASS

POTENTIAL MISMATCH

MANUAL REVIEW REQUIRED

Scan Label Only

The reviewer can upload a label without entering application information.

The system can extract:

Possible brand name

Class / type

Alcohol content

Net contents when confidently detected

Producer / bottler information when confidently detected

Country of origin when confidently detected

Government warning information

Front and Back Label Support

Front label image is required

Back label image is optional

Brand and class/type are checked mainly from the front label.

ABV, net contents, producer information, origin, and government warning are checked mainly from the back label.

Image Crop and Zoom

The user can move and zoom the label image and optionally use the selected crop for OCR.

OCR Confidence and Processing Time

Each result shows:

OCR confidence percentage

Confidence level: HIGH, MEDIUM, or LOW

Processing time in seconds

Explain Verification Result

LabelGuard AI includes a local rules-based explanation feature that can explain:

Why a result requires manual review

Which fields need attention

OCR confidence

Front-label OCR text

Back-label OCR text

Scan-only uncertain fields

This feature does not use an external generative AI service.

Technology Stack

Frontend

React

TypeScript

Vite

react-easy-crop

Backend

Python

FastAPI

Uvicorn

OpenCV

Tesseract OCR

NumPy

Verification

Local OCR

Text normalization

Rule-based field comparison

Context-aware percentage detection

Volume unit conversion

Conservative fuzzy matching

Human-in-the-loop review

Project Structure

ai-alcohol-label-verification/
├── backend/
│   ├── main.py
│   ├── ocr.py
│   └── verifier.py
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── .gitignore
└── README.md

How It Works

The reviewer uploads a front label and optionally a back label.

The browser can optionally crop the image before upload.

FastAPI receives the uploaded image files.

OpenCV prepares the images for OCR.

Tesseract performs targeted OCR passes.

OCR results are merged.

The verifier checks each application field against the appropriate label text.

The API returns field-level results, OCR confidence, processing time, and extracted text.

The React interface displays the results and provides reviewer-friendly explanations.

## Approach

I built LabelGuard AI as a standalone React and FastAPI prototype using local Tesseract OCR and OpenCV. The system processes front and back alcohol label images, extracts OCR text, and compares key fields against application information using deterministic verification rules. Brand and class/type are checked mainly from the front label, while ABV, net contents, producer information, origin, and government warning are checked mainly from the back label. I used conservative matching so uncertain OCR results are marked for manual review instead of forcing a false match or mismatch. I also added OCR confidence, processing time, image cropping, Scan Label Only mode, and a local explanation feature to make results easier for reviewers to understand.

Local Setup

Prerequisites

Install:

Python 3

Node.js and npm

Tesseract OCR

On macOS with Homebrew:

brew install tesseract

Confirm Tesseract is installed:

tesseract --version

Backend Setup

From the project root:

cd backend

Create a virtual environment:

python3 -m venv venv

Activate it:

source venv/bin/activate

Install dependencies:

pip install fastapi uvicorn python-multipart opencv-python pytesseract numpy

Start the backend:

uvicorn main:app --reload

Backend URL:

http://127.0.0.1:8000

FastAPI docs:

http://127.0.0.1:8000/docs

Frontend Setup

Open a second terminal:

cd frontend
npm install
npm run dev

Vite normally runs at:

http://localhost:5173

If port 5173 is already in use, Vite may use another local port such as 5174.

Verification Rules

Brand Name

Brand is checked mainly against the front label.

If the expected brand appears only on the back label, the result stays REVIEW instead of becoming MATCH.

Class / Type

The verifier recognizes common alcohol classes and types using exact and conservative fuzzy checks.

Alcohol Content

ABV is accepted only when a percentage appears in alcohol-related context.

Example:

Alcohol by volume: 35%

Net Contents

Supported units include:

mL

cL

L

fl. oz.

The verifier checks nearby OCR context so a serving-size value is not incorrectly treated as the package net contents.

Government Warning

The verifier compares OCR text against the expected government warning wording and checks recognizable phrase groups when OCR is incomplete.

Visual formatting, such as whether GOVERNMENT WARNING: is bold, still requires manual review.

OCR Confidence

OCR confidence represents confidence in recognized text, not legal or compliance confidence.

HIGH: 80% or higher

MEDIUM: 60% to 79.9%

LOW: below 60%

Performance

During local testing, front/back label verification commonly completed in approximately:

2 to 3 seconds

This is below the prototype target of about 5 seconds per verification.

Assumptions and Limitations

Clear label images improve OCR quality

Glare, curved bottles, small text, decorative fonts, and blur can reduce OCR accuracy

Government warning bold formatting is not automatically verified

Address extraction is intentionally conservative

Net contents may require manual review when OCR detects serving-size values

Full production batch processing is not implemented

The prototype does not directly integrate with an existing COLA system

This prototype assists human reviewers and does not make a final legal or compliance determination

Security and Privacy

The prototype uses local OCR and does not require an external OCR service.

For production use, additional controls would be needed, including authentication, secure transport, logging, file-retention rules, validation, and secrets management.

Future Improvements

Batch processing for larger label sets

Reviewer queue and audit history

Better producer and address extraction

Improved OCR preprocessing for curved or low-quality images

Automated image-quality checks

Azure-hosted deployment

Integration with an existing COLA workflow

Author

Rahel S. Gizaw