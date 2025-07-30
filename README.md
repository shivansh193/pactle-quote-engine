# Pactle Quote Generation Engine

This project is a deterministic quote generator that converts messy RFQs into accurate quotes. It includes a full web UI, role-based approvals, multi-currency support, and OCR for image-based RFQs.

## Setup & Running

**Prerequisites:** Docker and Docker Compose must be installed.

1.  **Build and Run the Container:**
    ```sh
    docker-compose up --build
    ```
2.  **Access the Application:**
    Open your web browser and navigate to `http://localhost:8000/`.

3.  **Run Tests:**
    ```sh
    # Open another terminal
    docker-compose exec api pytest
    ```