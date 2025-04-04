# Web Traffic Visualizer

This application visualizes simulated web traffic originating from various locations around the world on an interactive 3D globe. It shows the location of incoming packets and provides real-time statistics, including top source countries and overall request activity.

## Features

*   **3D Globe Visualization:** Uses Three.js to plot incoming traffic locations on a globe.
*   **Real-time Updates:** Fetches and displays data dynamically as it's processed by the backend.
*   **Traffic Simulation:** A Python script reads data from a CSV file (`ip_addresses.csv`) and sends it to the backend, simulating time intervals.
*   **Data Processing:** A Flask backend receives the data, performs reverse geocoding (using GeoPy/Nominatim) to determine the source country, and aggregates statistics.
*   **Interactive Elements:**
    *   Orbit controls allow zooming, panning, and rotating the globe.
    *   An information panel displays:
        *   Top 10 source countries by traffic volume.
        *   Total points currently displayed on the globe.
        *   Count of suspicious packets displayed.
        *   A real-time chart showing request activity (requests per second) over the last minute.
*   **Containerized:** The entire application (sender, backend, frontend) is containerized using Docker and Docker Compose for easy setup and deployment.

## Prerequisites

*   **Docker:** Ensure Docker is installed and running on your system. ([Install Docker](https://docs.docker.com/get-docker/))
*   **Docker Compose:** Ensure Docker Compose (usually included with Docker Desktop) is installed. ([Install Docker Compose](https://docs.docker.com/compose/install/))

## Setup

1.  **Clone the Repository (if applicable):**
    ```bash
    # git clone <repository-url>
    # cd <repository-directory>
    ```

2.  **Add Earth Texture:**
    *   You **must** obtain an equirectangular projection image of the Earth.
    *   Save this image as `earthmap.jpg` inside the `static/` directory.
    *   A common source is NASA's Blue Marble collection, but ensure you have the rights to use the image you choose.

## Running the Application

1.  **Build and Start Services:**
    Open a terminal in the project's root directory (where the `docker-compose.yml` file is located) and run:
    ```bash
    docker compose up --build
    ```
    This command will:
    *   Build the Docker images for the `backend` (Flask/Frontend) and `sender` services based on their respective `Dockerfile`s.
    *   Start the containers defined in `docker-compose.yml`.
    *   The `sender` service will wait briefly for the `backend` to start and then begin sending data from `ip_addresses.csv`.

2.  **Access the Visualizer:**
    Once the containers are running (you'll see logs from both services in your terminal), open your web browser and navigate to:
    [http://localhost:5001](http://localhost:5001)

    *(Note: The application runs on port 5001 on your host machine, mapped from port 5000 inside the backend container).*

3.  **View the Visualization:**
    You should see the 3D globe. After a short delay, points representing incoming traffic will start appearing. The information panel on the right will update with statistics and the activity chart.

## Stopping the Application

*   Press `Ctrl + C` in the terminal where `docker compose up` is running.
*   To remove the containers (and network), you can run:
    ```bash
    docker compose down
    ```

## Project Structure

```
.
├── app.py                 # Flask backend logic
├── sender.py              # Python script to send traffic data
├── ip_addresses.csv       # Input traffic data
├── requirements.txt       # Python dependencies
├── Dockerfile.backend     # Dockerfile for Flask app + frontend
├── Dockerfile.sender      # Dockerfile for the sender script
├── docker-compose.yml     # Docker Compose configuration
├── templates/
│   └── index.html         # Main HTML page for the frontend
├── static/
│   ├── main.js            # Three.js and Chart.js logic
│   ├── style.css          # CSS styles for the frontend
│   └── earthmap.jpg       # REQUIRED: Earth texture map (add this file)
└── README.md              # This file
``` 