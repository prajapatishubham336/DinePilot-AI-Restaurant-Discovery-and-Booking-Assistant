# DinePilot-AI-Restaurant-Discovery-and-Booking-Assistant
AI-powered restaurant discovery and table booking assistant with location search, restaurant ranking, menu preview, slot availability, customer bookings, and owner management.


# 🍽️ DinePilot AI — Restaurant Discovery & Booking Assistant

DinePilot AI is an AI-powered restaurant discovery and booking assistant that helps users find nearby restaurants, explore restaurant information, view available menu previews, check opening hours, select booking slots, and manage their reservations.

The system also provides an Owner Dashboard where restaurant owners can configure tables, create time slots, monitor availability, and approve or reject booking requests.

DinePilot is designed as a practical real-world AI application combining LLMs, tool calling, location services, restaurant data, and booking management into a single interactive platform.

---

## 🚀 Features

### 👤 User Features

- 📍 Search restaurants using location
- 🔎 Discover nearby restaurants
- ⭐ Restaurant ranking based on distance and available information
- 🏪 View restaurant details
- 📍 View restaurant address
- 🕒 View restaurant opening hours
- 🌐 Open official restaurant website
- 🍕 View menu preview when publicly available
- 📅 Select booking date
- ⏰ Select available booking time
- 👥 Select number of guests
- 📋 View personal bookings
- ❌ Cancel existing bookings
- ✅ Booking status tracking

---

### 🏪 Owner Dashboard

Restaurant owners can manage their restaurant operations through a dedicated dashboard.

Features include:

- ➕ Add restaurant
- 🪑 Configure total tables
- 👥 Configure seats per table
- 🕒 Create booking time slots
- 📊 Monitor slot availability
- 📋 View booking requests
- ✅ Confirm bookings
- ❌ Reject bookings
- 🔄 Automatically release tables when a booking is cancelled or rejected

---

## 🤖 AI Capabilities

DinePilot AI uses an LLM-powered workflow to understand user requests and coordinate different restaurant-related operations.

The AI workflow can handle tasks such as:

- Understanding restaurant search requirements
- Location processing
- Restaurant discovery
- Restaurant ranking
- Restaurant information retrieval
- Menu retrieval
- Booking-related operations
- Cancellation workflows

The application uses tool-based AI orchestration so that the model can work with actual application functions instead of generating unsupported restaurant information.

---

## 🧠 System Architecture

```text
                         ┌──────────────────────┐
                         │      User Query      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    AI Planner / LLM  │
                         └──────────┬───────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
     ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
     │ Location Tool │      │ Restaurant    │      │ Booking Tool  │
     │               │      │ Search Tool   │      │               │
     └───────────────┘      └───────────────┘      └───────────────┘
             │                      │                      │
             ▼                      ▼                      ▼
        Nominatim              OpenStreetMap            SQLite
             │                 / Overpass DB
             │                      │
             └──────────────┬───────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │ Restaurant Results   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Streamlit Dashboard  │
                  └──────────────────────┘
```

## 🌐 Data Sources

DinePilot uses publicly available location and restaurant information sources.

### OpenStreetMap

OpenStreetMap is used to retrieve restaurant and location-related information.

Information can include:

- Restaurant name
- Coordinates
- Address
- Cuisine
- Opening hours
- Website
- Phone number

### Nominatim

Nominatim is used for:

- Converting user location text into coordinates
- Reverse geocoding restaurant coordinates into readable addresses

### Overpass API

Overpass is used to query nearby restaurant data from OpenStreetMap.

### Restaurant Website

When available, the restaurant's public website can be used as a fallback for:

- Address
- Opening hours
- Menu information

The application does not invent missing information. When information is unavailable, the UI displays an appropriate fallback message.

---

## 🗺️ Location Flow

```text
User Location
      │
      ▼
Geocoding
      │
      ▼
Latitude + Longitude
      │
      ▼
Nearby Restaurant Search
      │
      ▼
Restaurant Ranking
      │
      ▼
Top Restaurant Results
```

---

## 📅 Booking System

DinePilot includes a table-based booking system.

Each restaurant can configure:

```text
Restaurant
   │
   ├── Total Tables
   ├── Seats per Table
   │
   └── Time Slots
          │
          ├── 18:00
          ├── 18:30
          ├── 19:00
          ├── 19:30
          └── 20:00
```

When a customer books a table, the application calculates the required number of tables based on the number of guests.

### Example

```text
Seats per table = 4
Guests          = 7

Required tables = 2
```

The available table count is updated for that slot.

When a booking is cancelled or rejected:

```text
Cancelled Booking
        │
        ▼
Reserved Tables Released
        │
        ▼
Slot Availability Updated
```

---

## 📊 Booking Status

Bookings can move through different states:

```text
PENDING
   │
   ├──► CONFIRMED
   │
   └──► REJECTED

CONFIRMED
   │
   └──► CANCELLED
```

The booking status is managed through the application database.

---

## 🖥️ Application Pages

### Discover

Users can search and discover nearby restaurants.

### My Bookings

Users can enter their email or phone number and view their booking history.

### Owner Dashboard

Restaurant owners can:

- Configure restaurant capacity
- Create time slots
- Monitor table availability
- Confirm bookings
- Reject bookings

### Agent Activity

The application can expose AI workflow and tool activity to provide visibility into the assistant's operations.

---

## 🛠️ Tech Stack

### Programming Language

- Python

### Frontend

- Streamlit

### AI / LLM

- Groq API
- LangChain
- LangGraph
- Tool Calling

### Location & Restaurant Data

- OpenStreetMap
- Nominatim
- Overpass API

### Database

- SQLite

### Web / API

- Requests
- BeautifulSoup

### Data Processing

- Pandas

### Environment Management

- python-dotenv

---

## 📂 Project Structure

```text
dinepilot/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── availability.py
│   ├── owner.py
│   ├── tools.py
│   ├── notification.py
│   ├── graph.py
│   ├── auth.py
│   └── agent.py
│
├── tests/
│   └── test_smoke.py
│
├── streamlit_app.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 📌 File Responsibilities

### `streamlit_app.py`

Main Streamlit application.

Handles:

- User interface
- Restaurant discovery
- Restaurant details
- Booking form
- My Bookings
- Owner Dashboard access
- Navigation

---

### `app/tools.py`

Contains external-data and application tools.

Handles:

- Location geocoding
- Reverse geocoding
- Nearby restaurant search
- Restaurant information
- Website information
- Opening hours extraction
- Menu preview extraction

---

### `app/db.py`

Handles booking database operations.

Includes:

- Saving bookings
- Listing bookings
- Fetching booking details
- Cancelling bookings
- Updating booking status

---

### `app/availability.py`

Handles restaurant table inventory.

Includes:

- Restaurant table configuration
- Time-slot creation
- Table reservation
- Table release
- Availability calculation

---

### `app/owner.py`

Contains the restaurant owner management dashboard.

Handles:

- Restaurant configuration
- Table capacity setup
- Time-slot creation
- Availability monitoring
- Booking request management
- Booking confirmation
- Booking rejection

---

### `app/notification.py`

Handles notification-related functionality.

Can be used for:

- Booking notifications
- Confirmation notifications
- Cancellation notifications
- Reservation status updates

---

### `app/graph.py`

Contains the AI workflow and graph orchestration logic.

Handles the flow between:

- User requests
- AI reasoning
- Tools
- Restaurant search
- Booking-related actions

---

### `app/auth.py`

Contains authentication and access-control functionality.

Used for:

- Owner authentication
- Protected dashboard access
- Session-based authorization

---

### `app/agent.py`

Contains the AI agent logic.

Handles:

- User intent understanding
- Tool selection
- Tool execution
- AI-assisted restaurant workflows

---

### `app/config.py`

Stores application configuration such as:

- Environment variables
- API configuration
- Database path
- External service URLs

---

### `tests/test_smoke.py`

Contains basic smoke tests to verify that the application components can be imported and run correctly.

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/prajapatishubham336/DinePilot-AI-Restaurant-Discovery-and-Booking-Assistant.git
```

### 2. Open the project

```bash
cd DinePilot-AI-Restaurant-Discovery-and-Booking-Assistant
```

### 3. Create and activate the environment

Using Conda:

```bash
conda create -n llmapp python=3.11
```

Activate the environment:

```bash
conda activate llmapp
```

---

## 📦 Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Create a `.env` file in the project root.

```env
GROQ_API_KEY=your_groq_api_key
ADMIN_PASSWORD=your_owner_password
```

Make sure `.env` is included in `.gitignore`.

**Never commit API keys, passwords, or other sensitive credentials to GitHub.**

---

## ▶️ Run the Application

Start the application from the project root:

```bash
python -m streamlit run streamlit_app.py
```

The Streamlit application will open in your browser.

---

## 🔄 Application Workflow

### Restaurant Discovery

```text
User
 │
 ▼
Enter Location
 │
 ▼
Geocode Location
 │
 ▼
Search Nearby Restaurants
 │
 ▼
Collect Restaurant Data
 │
 ▼
Rank by Distance
 │
 ▼
Display Restaurant Results
```

### Restaurant Information

```text
Restaurant Selected
       │
       ├── Address
       ├── Cuisine
       ├── Opening Hours
       ├── Website
       ├── Phone
       └── Menu Preview
```

### Booking Workflow

```text
Select Restaurant
       │
       ▼
Select Date
       │
       ▼
Select Time
       │
       ▼
Enter Guests
       │
       ▼
Check Available Tables
       │
       ▼
Reserve Tables
       │
       ▼
Create Booking
       │
       ▼
PENDING
```

The owner can then confirm or reject the booking.

---

## 🧮 Table Availability Logic

DinePilot calculates table requirements using the configured seating capacity.

```text
Required Tables = Ceiling(
    Number of Guests / Seats per Table
)
```

### Example

```text
Guests = 9
Seats per Table = 4

Required Tables = Ceiling(9 / 4)
                 = 3
```

This helps prevent overbooking for the configured restaurant capacity.

---

## 🔒 Safety & Data Handling

DinePilot follows important application-level safeguards:

- Public website fetching is restricted to publicly reachable URLs.
- Missing restaurant information is not fabricated.
- Website information is treated as a fallback when OpenStreetMap data is incomplete.
- Booking ownership can be verified using the customer's email or phone.
- API keys are loaded through environment variables.
- Sensitive environment variables should never be committed to GitHub.

---

## 💡 Why DinePilot AI?

Traditional restaurant applications usually separate restaurant discovery, information search, and booking into multiple workflows.

DinePilot combines them into one AI-assisted experience:

```text
Discover
   ↓
Understand
   ↓
Compare
   ↓
Explore
   ↓
Check Availability
   ↓
Book
   ↓
Manage Reservation
```

This makes the application closer to a real-world AI assistant rather than a simple restaurant listing application.

---

## 🎯 Use Cases

DinePilot can be useful for:

- 🍽️ Dinner planning
- 👨‍👩‍👧 Family restaurant discovery
- 💑 Date-night restaurant search
- 🎉 Group dining
- 🏢 Corporate dinner planning
- 📅 Restaurant reservation management
- 🏪 Restaurant owner booking management

---

## 🔮 Future Enhancements

Possible future improvements include:

- 💳 Online payment integration
- 📧 Booking confirmation emails
- 📱 SMS/WhatsApp notifications
- 🗺️ Interactive restaurant maps
- ❤️ Favorite restaurants
- ⭐ User reviews and ratings
- 🔍 Advanced cuisine and price filters
- 🤖 More advanced AI agent orchestration
- 🧾 Digital booking receipts
- 📈 Restaurant analytics dashboard
- 👤 User authentication
- ☁️ Cloud database support
- 🚀 Production deployment with FastAPI backend

---

## 📈 Project Highlights

This project demonstrates practical implementation of:

- Generative AI
- LLM applications
- AI Agents
- Tool Calling
- LangChain
- LangGraph
- Groq API
- Location-based search
- Web data extraction
- REST API consumption
- Database management
- Table inventory management
- Reservation workflows
- Streamlit dashboard development
- AI workflow orchestration
- Real-world AI application design

---

## 🧑‍💻 Author

**Shubham Prajapati**

AI / ML & Generative AI Project

---

## 📄 License

This project is licensed under the MIT License.

See the `LICENSE` file for details.
