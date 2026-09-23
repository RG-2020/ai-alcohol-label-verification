# LabelGuard AI

**Alcohol Label Verification Prototype by Rahel S. Gizaw**

LabelGuard AI is a lightweight prototype for scanning alcohol labels and comparing label text against application information. The project is designed to support a human reviewer by extracting label text with local OCR, checking selected fields with deterministic verification rules, and clearly identifying items that require manual review.

The prototype is intentionally conservative: uncertain OCR is not treated as a confirmed match or mismatch.

Features

Verify Against Application

The reviewer can enter application information and upload front and optional back label images. LabelGuard AI checks:

Brand name

Class / type

Alcohol content (ABV)

Net contents

Producer / bottler name

Producer / bottler address or country of origin

Government warning wording

Each field is returned as:

MATCH

MISMATCH

REVIEW

The overall result is:

PASS

POTENTIAL MISMATCH

MANUAL REVIEW REQUIRED

Scan Label Only

The reviewer can upload a label without entering application data. LabelGuard AI extracts readable information from the image and returns conservative structured results.

Examples include:

Possible brand name

Class / type

Alcohol content

Net contents when confidently identified

Producer / bottler information when confidently identified

Country of origin when confidently identified

Government warning detection

Front and Back Label Support

The prototype accepts:

Required front label image

Optional back label image

The verifier uses the label side that is most appropriate for each field. For example, brand and class/type are checked mainly on the front label, while ABV, producer information, net contents, origin, and the government warning are checked mainly on the back label.

Manual Crop and Zoom

The React interface allows the reviewer to move and zoom label images and optionally use the selected crop for OCR.

OCR Confidence and Processing Time

Each result displays:

OCR confidence percentage

Confidence level: HIGH, MEDIUM, or LOW

Processing time in seconds

Explain Verification Result

LabelGuard AI includes a local rules-based explanation feature. It can explain:

Why a result requires manual review

Which fields need attention

OCR confidence

Front-label OCR text

Back-label OCR text

Scan-only uncertain fields

This feature does not call an external generative AI service.

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

Verification Approach

Local OCR

Text normalization

Rule-based field comparison

Context-aware percentage detection

Unit conversion for volume comparisons

Conservative fuzzy matching

Human-in-the-loop review

Project Structure

ai-alcohol-label-verification/
├── backend/
│   ├── main.py
│   ├── ocr.py
│   ├── verifier.py
│   └── venv/
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
└── README.md

The local venv and node_modules directories should not be committed to Git.

How It Works

The reviewer uploads a front label and optionally a back label.

The browser can optionally crop the images before upload.

FastAPI receives the images.

OpenCV prepares the images for OCR.

Tesseract performs multiple targeted OCR passes.

OCR results are merged into one readable result.

The verifier checks each application field against the appropriate label text.

The API returns field-level results, OCR confidence, processing time, and extracted text.

The React interface displays the result and provides reviewer-friendly explanations.

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

Create a virtual environment if one does not already exist:

python3 -m venv venv

Activate it:

source venv/bin/activate

Install the backend dependencies:

pip install fastapi uvicorn python-multipart opencv-python pytesseract numpy

Start the FastAPI server:

uvicorn main:app --reload

The backend should run at:

http://127.0.0.1:8000

FastAPI documentation is available at:

http://127.0.0.1:8000/docs

Frontend Setup

Open a second terminal and run:

cd frontend
npm install
npm run dev

Vite normally starts at:

http://localhost:5173

If port 5173 is already in use, Vite may use another local port such as 5174.

API Endpoints

POST /verify

Verifies uploaded label images against application values.

Inputs include:

front_image

back_image (optional)

Brand name

Class / type

Alcohol content

Net contents

Producer / bottler name

Producer / bottler address or country of origin

POST /scan

Scans uploaded label images without application comparison and returns conservative structured extraction.

Verification Rules

Brand Name

Brand is checked mainly against the front label. If the expected brand appears only on the back label, the result remains REVIEW instead of being promoted to MATCH.

Class / Type

Known alcohol classes and types are recognized with exact and conservative fuzzy checks. A broad type such as Rum does not automatically contradict a more specific type such as Spiced Rum.

Alcohol Content

ABV is accepted only when a percentage appears in alcohol-related context, such as:

Alcohol by volume: 35%

Unrelated percentages are not used to create a confident ABV match or mismatch.

Net Contents

Supported units include:

mL

cL

L

fl. oz.

Values are converted internally to milliliters for comparison.

The verifier also checks nearby OCR context so a serving-size statement such as:

Serving size: 1.5 fl. oz. (44 mL)

is not incorrectly treated as package net contents.

Producer / Bottler Information

Producer and bottler fields use normalized text comparison. Unclear OCR remains REVIEW.

Government Warning

The verifier compares OCR text against the expected government warning wording and also checks recognizable phrase groups when OCR is incomplete.

A result can remain REVIEW even when most warning language is detected because OCR may miss words, punctuation, or formatting.

Government Warning Formatting Limitation

Plain OCR text can evaluate wording but cannot reliably prove visual formatting such as whether the heading is bold.

For that reason, LabelGuard AI does not claim that bold formatting has been verified automatically. Visual formatting should remain part of human review.

OCR Confidence

OCR confidence represents confidence in recognized text, not a legal or compliance confidence score.

Current UI levels are:

HIGH: 80% or higher

MEDIUM: 60% to 79.9%

LOW: below 60%

Low or medium OCR confidence does not automatically mean a label is incorrect. It indicates that human review may be appropriate.

Performance

During local testing on the development machine, individual front/back label verification commonly completed in approximately:

2 to 3 seconds

This is below the prototype target of approximately 5 seconds per verification.

Performance depends on:

Image size

Image quality

Crop selection

OCR readability

Local hardware

Design Decisions

Local OCR

Tesseract runs locally rather than sending label images to an external OCR API.

This approach was chosen because:

The prototype can work without outbound OCR service calls.

It is more suitable for restricted or government-network environments.

Label images remain on the local processing path.

It avoids external API latency and dependency during the prototype.

Conservative Verification

The system avoids forcing uncertain OCR into a binary result.

When evidence is incomplete, LabelGuard AI returns REVIEW so a human reviewer can make the final decision.

Deterministic Rules

Field verification uses deterministic rules instead of an external LLM. This makes individual decisions easier to explain and reproduce.

Assumptions

The uploaded images contain the relevant front and/or back label.

A clear crop improves OCR quality.

Application values are entered accurately.

English-language OCR is the primary target of this prototype.

Front and back label information may appear in different visual locations.

The prototype assists a reviewer; it does not replace official regulatory review.

Current Limitations

OCR quality decreases with glare, curved bottles, decorative fonts, very small text, blur, or low-resolution images.

OCR may miss parts of a brand or warning even when they are visible to a person.

Government warning visual formatting such as bold text is not automatically verified.

Address extraction is intentionally conservative.

Scan Only brand extraction is conservative and may return Not confidently detected.

Net contents can require manual review when OCR only finds serving-size or nutrition-panel volumes.

The prototype does not currently provide full production batch-processing infrastructure.

The prototype does not integrate directly with an existing COLA system.

This is a prototype and not a final legal or compliance determination system.

Security and Privacy

The current prototype does not require an external OCR service. Label OCR is processed locally by the backend.

For a production deployment, additional controls should be added as required, including:

Authentication and authorization

Secure transport

Logging and audit controls

File-retention rules

Malware/file validation

Production secrets management

Infrastructure monitoring

Future Improvements

Possible next steps include:

Batch processing for larger label sets

Reviewer queue and audit history

More robust producer/address extraction

Additional OCR preprocessing for curved or low-quality bottle images

Automated image-quality checks

More comprehensive product-type dictionaries

Containerized deployment

Azure-hosted production architecture

Integration with an existing application or COLA workflow

Prototype Status

The current prototype supports both:

Verify Against Application

Scan Label Only

It demonstrates local OCR, field-level verification, conservative review handling, explainable results, and sub-5-second local processing in the tested examples.

Author

Rahel S. Gizaw