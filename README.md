# NagarPravah: City Flow

**"Extracting Insights from Urban Noise"**

NagarPravah (City Flow) is an intelligent urban information system that transforms noisy, unstructured data from multiple city sources into actionable insights. The system leverages a sophisticated multi-agent architecture to collect, normalize, analyze, and synthesize city-related data from various sources including social media (Twitter, Facebook), news APIs, events APIs, and other urban data streams.

The core philosophy of NagarPravah is to **get insights out of noise** - taking fragmented, chaotic urban data and converting it into a coherent, real-time pulse of the city that citizens, planners, and decision-makers can understand and act upon.

## 🏛️ Architecture Overview

NagarPravah follows a microservices architecture built on Google Cloud Platform, utilizing Firebase and various Google services for scalable, event-driven processing. The system transforms noisy urban data into structured insights through a multi-stage pipeline.

```
                    🌐 NOISY DATA SOURCES
    ┌─────────────┬─────────────┬─────────────┬─────────────┐
    │   Twitter   │  Facebook   │  News APIs  │ Events APIs │
    │   Social    │   Posts     │  Articles   │ City Events │
    └─────────────┴─────────────┴─────────────┴─────────────┘
                                  │
                                  ▼
┌─────────────────┐    ┌──────────────────────────────────────────┐
│   observer.py   │────│         Google Pub/Sub Topics           │
│  (Orchestrator) │    │        (Firebase Integration)           │
└─────────────────┘    └──────────────────────────────────────────┘
                              │                    │
                              │                    │
                    ┌─────────▼─────────┐ ┌───────▼────────┐
                    │ analyzed-topic    │ │ synthesized-   │
                    │                   │ │ topic          │
                    └─────────┬─────────┘ └───────┬────────┘
                              │                   │
        ┌─────────────────────┼───────────────────┼─────────────────────┐
        │                     │                   │                     │
        ▼                     ▼                   ▼                     ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ scout-agent │    │analyze-agent│    │ maps-agent  │    │synthesize-  │
│(Normalize & │    │(Dedupe &    │    │(Visual Maps │    │agent        │
│ Transform)  │    │ Insights)   │    │& Geospatial)│    │(Event Gen)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
        │                     │                   │                     │
        └─────────────────────┼───────────────────┼─────────────────────┘
                              │                   │
                              ▼                   ▼
                    ┌─────────────────────────────────┐
                    │      Google Firestore DB       │
                    │   (Firebase Integration)       │
                    │  - scouted_data                 │
                    │  - analyzed-event               │
                    │  - synthesized_events           │
                    │  - user_preferences             │
                    │  - job_state_tracking           │
                    └─────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────┐
                    │    personalize-agent            │
                    │  (User-Specific Insights)       │
                    └─────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────┐
                    │   Conversational Agent          │
                    │  (City's Pulse Interface)       │
                    │   - LangChain Integration       │
                    │   - Google GenAI                │
                    └─────────────────────────────────┘
```

## 🔧 Components

### Observer Service (`observer.py`)
The central orchestrator that manages the data processing pipeline:
- Monitors Firestore for new data
- Triggers cloud functions via Pub/Sub messages
- Manages job state and ensures data consistency
- Implements cursor-based pagination for efficient data processing
- Runs continuous orchestration loops

**Key Features:**
- Batched processing (20 items per batch for Stage 1, 5 for Stage 2)
- State tracking with correlation IDs
- Automatic retry and acknowledgment handling
- FastAPI-based callback endpoint for agent responses

### Cloud Functions (Agents)

#### 1. Scout Agent (`backend/agents/scout-agent/`)
**Purpose:** Data Collection & Normalization from Noisy Sources
- **Data Sources:** Twitter, Facebook, News APIs, Events APIs, RSS feeds, and other urban data streams
- **Core Function:** Normalizes and transforms heterogeneous data into a single, consistent format
- **Data Standardization:** Converts varying data structures, formats, and schemas into unified format
- **Storage:** Stores normalized data in Firestore `scouted_data` collection
- **Trigger:** Pub/Sub messages or scheduled events
- **Output:** Clean, structured data ready for analysis

#### 2. Analyze Agent (`backend/agents/analyze-agent/`)
**Purpose:** Data Deduplication, Merging & High-Level Insights Generation
- **Deduplication:** Identifies and removes duplicate entries from multiple sources
- **Data Merging:** Combines related data points from different sources
- **Insight Generation:** 
  - Generates priority scores for events based on relevance and impact
  - Determines event status (ongoing, upcoming, completed)
  - Performs sentiment analysis and categorization
  - Extracts key themes and trends
- **Storage:** Stores analyzed data in Firestore `analyzed-event` collection
- **Trigger:** `analyzed-topic` Pub/Sub messages

#### 3. Synthesize Agent (`backend/agents/synthesize-agent/`)
**Purpose:** Event Generation & Relationship Analysis
- **Event Creation:** Generates comprehensive events from analyzed data
- **Key Outputs:**
  - **Overall Summaries:** High-level event descriptions and context
  - **Consequential Relationships:** Identifies cause-and-effect relationships between events
  - **Engagement Metrics:** Calculates engagement counts and social impact scores
  - **Trend Analysis:** Identifies emerging patterns and connections
- **Storage:** Stores synthesized events in Firestore `synthesized_events` collection
- **Trigger:** `synthesized-topic` Pub/Sub messages

#### 4. Maps Agent (`backend/agents/maps-agent/`)
**Purpose:** Geospatial Visualization & Location-Based Processing
- **Visual Representation:** Creates various map visualizations of city events
- **Geographic Processing:**
  - Geocodes addresses and location references using Google Maps API
  - Creates heat maps of event density
  - Generates location-based clusters and patterns
  - Provides spatial relationship analysis
- **Integration:** Google Maps API, Google Places API
- **Output:** Interactive maps, geospatial data layers, location insights
- **Trigger:** Pub/Sub messages

#### 5. Personalize Agent (`backend/agents/personalize-agent/`)
**Purpose:** User-Specific Content Customization
- **Personalization Factors:**
  - User location and proximity to events
  - Personal preferences and interests
  - Historical interaction patterns
  - Demographic and behavioral data
- **Custom Views:** Creates tailored event feeds for individual users
- **Recommendation Engine:** Suggests relevant events and information
- **Privacy:** Ensures user data protection and consent management
- **Storage:** User preferences stored in Firestore `user_preferences` collection
- **Trigger:** Pub/Sub messages

### Conversational Agent (`conv_agent_vertex/`)
**Purpose:** Conversational Interface to the City's Pulse
- **Core Concept:** Provides natural language access to the city's real-time pulse
- **Technology Stack:**
  - Flask-based web application
  - LangChain integration for conversation management
  - Google GenAI (Gemini) for natural language processing
- **Capabilities:**
  - Query synthesized events and insights
  - Ask questions about city trends and patterns
  - Get personalized recommendations
  - Access real-time city analytics
- **Data Access:** Leverages all processed data from other agents
- **Deployment:** Containerized service with Docker
- **Interface:** RESTful API and web interface

### Architecture Diagram

<img width="2354" height="1500" alt="image" src="https://github.com/user-attachments/assets/49ba65da-4305-4669-9a86-3d7465c7aaca" />

### App Screen

<img width="1702" height="931" alt="image" src="https://github.com/user-attachments/assets/ca185f9b-bcb1-4a13-a1ed-2ba4b334a81c" />

<img width="1719" height="958" alt="image" src="https://github.com/user-attachments/assets/6355c0cb-0dbc-4756-906b-0bc8e5ce9322" />

<img width="1710" height="967" alt="image" src="https://github.com/user-attachments/assets/bcbf0251-f0d5-4792-a686-d9730ed41b59" />


## 🔧 Google Cloud Services & Technologies Used

NagarPravah leverages a comprehensive suite of Google Cloud Platform services:

### Core Infrastructure
- **Google Cloud Functions:** Serverless execution environment for all agents
- **Google Cloud Pub/Sub:** Message queuing and event-driven communication
- **Google Cloud Run:** Container deployment for conversational agent
- **Google Compute Engine:** Infrastructure for observer service (optional)

### Database & Storage
- **Firebase:** Primary platform integration
- **Google Firestore:** NoSQL document database for all data storage
- **Firebase Admin SDK:** Server-side Firebase integration
- **Firebase Authentication:** User management and security (future enhancement)

### AI & Machine Learning
- **Google GenAI (Gemini):** Large language model for conversational interface
- **Google Cloud Translation API:** Multi-language support
- **Vertex AI:** AI platform integration (conversational agent)

### Mapping & Location Services
- **Google Maps API:** Geocoding and mapping services
- **Google Places API:** Location data and place information
- **Google Maps JavaScript API:** Interactive map visualizations

### Development & Integration
- **LangChain:** Framework for building LLM applications
- **Google Cloud SDK:** Development and deployment tools
- **Firebase CLI:** Command-line tools for Firebase

### Frontend Application
- **Firebase Studio** : Our full frontend Application is Built using Firebase Studio in Typescript

## 🚀 Setup and Deployment

### Prerequisites
- Google Cloud Platform account
- Firebase project with Firestore enabled
- Service account credentials (`nagar-pravah-fb-b49a37073a4a.json`)
- Python 3.9+

### Environment Variables
```bash
# Required for all agents
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GCP_PROJECT_ID=nagar-pravah-v1
FIRESTORE_PROJECT_ID=nagar-pravah-fb

# API Keys
GEMINI_API_KEY=your_gemini_api_key
TWITTER_CONSUMER_KEY=your_twitter_key
TWITTER_CONSUMER_SECRET=your_twitter_secret
GOOGLEMAPS_API_KEY=your_maps_api_key

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key
```

### Local Development

1. **Clone the repository:**
```bash
git clone <repository-url>
cd Nagar-Pravah-V1-main
```

2. **Install dependencies for Observer service:**
```bash
pip install fastapi uvicorn google-cloud-firestore google-cloud-pubsub
```

3. **Install dependencies for individual agents:**
```bash
cd backend/agents/analyze-agent
pip install -r requirement.txt
```

4. **Run Observer service:**
```bash
uvicorn observer:app --reload
```

5. **Run Conversational Agent:**
```bash
cd conv_agent_vertex
pip install -r requirements.txt
python app/main.py
```

### Cloud Deployment

#### Deploy Cloud Functions
```bash
# Deploy each agent as a Cloud Function
cd backend/agents/analyze-agent
gcloud functions deploy analyze-agent \
  --runtime python39 \
  --trigger-topic analyzed-topic \
  --entry-point handle_cloud_event

cd ../scout-agent
gcloud functions deploy scout-agent \
  --runtime python39 \
  --trigger-topic scout-topic \
  --entry-point main

# Repeat for other agents...
```

#### Deploy Observer Service
```bash
# Deploy to Cloud Run or Compute Engine
gcloud run deploy observer-service \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Create Pub/Sub Topics
```bash
gcloud pubsub topics create analyzed-topic
gcloud pubsub topics create synthesized-topic
gcloud pubsub topics create scout-topic
gcloud pubsub topics create maps-topic
gcloud pubsub topics create personalize-topic
```

#### Deploy Conversational Agent
```bash
cd conv_agent_vertex
gcloud run deploy conv-agent \
  --source . \
  --platform managed \
  --region us-central1
```

## 📊 Data Flow: From Noise to Insights

NagarPravah's data processing pipeline transforms chaotic urban data into actionable insights:

1. **Data Ingestion:** Scout agent continuously monitors and collects data from noisy sources (Twitter, Facebook, News APIs, Events APIs)
2. **Normalization:** Raw, heterogeneous data is transformed into a standardized format
3. **Storage:** Normalized data stored in Firestore `scouted_data` collection
4. **Orchestration:** Observer service detects new data and triggers processing pipeline
5. **Analysis & Deduplication:** Analyze agent removes duplicates, merges related data, and generates insights with priority scores
6. **Event Synthesis:** Synthesize agent creates comprehensive events with summaries, relationships, and engagement metrics
7. **Geospatial Processing:** Maps agent adds location context and creates visualizations
8. **Personalization:** Personalize agent customizes content based on user preferences and location
9. **Conversational Access:** Users interact with processed insights via natural language interface
10. **Real-time Updates:** Continuous pipeline ensures fresh, up-to-date city pulse information

## 🗃️ Database Schema

### Firebase Firestore Collections

#### `scouted_data` (Normalized Raw Data)
```json
{
  "content": "Event or news content from various sources",
  "location": "Standardized location information",
  "source": "twitter|facebook|news_api|events_api|rss",
  "original_format": "Source-specific metadata",
  "data_quality_score": 0.85,
  "createdAt": "2024-07-26T09:15:22.123+05:30",
  "scoutedAt": "Processing timestamp"
}
```

#### `analyzed-event` (Deduplicated & Enriched Data)
```json
{
  "original_content": "Raw content from scout agent",
  "analyzed_content": "Processed and enriched content",
  "priority_score": 8.5,
  "status": "ongoing|upcoming|completed",
  "sentiment": "positive|negative|neutral",
  "sentiment_score": 0.7,
  "category": "event|news|traffic|weather|emergency",
  "themes": ["technology", "community", "innovation"],
  "location": "Standardized location with coordinates",
  "duplicate_ids": ["id1", "id2"],
  "confidence_score": 0.92,
  "createdAt": "ISO timestamp"
}
```

#### `synthesized_events` (Generated Events with Relationships)
```json
{
  "event_id": "unique_event_identifier",
  "title": "Generated event title",
  "overall_summary": "Comprehensive event description",
  "engagement_count": 1250,
  "social_impact_score": 7.8,
  "consequential_relationships": [
    {
      "related_event_id": "event_123",
      "relationship_type": "causes|leads_to|related_to",
      "strength": 0.85
    }
  ],
  "trend_indicators": ["increasing_interest", "viral_potential"],
  "source_events": ["analyzed_event_1", "analyzed_event_2"],
  "createdAt": "ISO timestamp"
}
```

#### `user_preferences` (Personalization Data)
```json
{
  "user_id": "unique_user_identifier",
  "location_preferences": {
    "primary_location": "Koramangala, Bangalore",
    "radius_km": 10,
    "areas_of_interest": ["Indiranagar", "HSR Layout"]
  },
  "category_preferences": {
    "events": 0.9,
    "technology": 0.8,
    "food": 0.6,
    "traffic": 0.3
  },
  "engagement_history": ["event_1", "event_2"],
  "notification_settings": {
    "priority_threshold": 7.0,
    "frequency": "real_time|hourly|daily"
  },
  "createdAt": "ISO timestamp",
  "lastUpdated": "ISO timestamp"
}
```

#### `job_state_tracking` (Pipeline Management)
```json
{
  "stage1_cursor": {"last_createdAt": "timestamp"},
  "stage2_cursor": {"last_createdAt": "timestamp"},
  "pipeline_metrics": {
    "processed_today": 1450,
    "duplicates_removed": 120,
    "events_generated": 85
  }
}
```

## 🔍 Monitoring and Logging

- **Structured Logging:** All agents implement comprehensive logging with correlation IDs
- **Pipeline Metrics:** Observer service tracks job states, processing rates, and success metrics
- **Auto-scaling:** Cloud Functions automatically scale based on Pub/Sub message volume
- **Real-time Sync:** Firestore provides real-time data synchronization across all agents
- **Performance Monitoring:** Google Cloud Monitoring integration for system health
- **Error Tracking:** Google Cloud Error Reporting for issue detection and resolution
- **Data Quality Metrics:** Tracking of deduplication rates, confidence scores, and processing accuracy

## 💡 Key Features & Capabilities

### Noise-to-Signal Transformation
- **Multi-source Integration:** Aggregates data from Twitter, Facebook, News APIs, Events APIs
- **Intelligent Deduplication:** Advanced algorithms to identify and merge duplicate content
- **Priority Scoring:** AI-driven prioritization based on relevance, impact, and engagement
- **Real-time Processing:** Continuous pipeline for up-to-date city insights

### Advanced Analytics
- **Trend Detection:** Identifies emerging patterns and viral content
- **Relationship Mapping:** Discovers consequential relationships between events
- **Sentiment Analysis:** Understands public mood and reactions
- **Geospatial Intelligence:** Location-based event clustering and heat mapping

### User Experience
- **Conversational Interface:** Natural language queries about city pulse
- **Personalized Content:** Tailored recommendations based on user preferences
- **Interactive Maps:** Visual representation of city events and trends
- **Real-time Notifications:** Alerts for high-priority events and personalized interests

## 🧪 Testing

### Mock Data
The project includes comprehensive mock data for testing the complete pipeline:
- `backend/event_mock_data.json` - Sample events from various Bangalore sources
- `backend/traffic_mock_data.json` - Traffic and transportation information
- `backend/weather_mock_data.json` - Weather data and alerts
- `backend/scout_data_openai.json` - AI-processed sample data

### Testing Strategy
- **Unit Tests:** Individual agent functionality testing
- **Integration Tests:** End-to-end pipeline validation
- **Data Quality Tests:** Deduplication and normalization accuracy
- **Performance Tests:** Load testing for high-volume data processing

### Running Tests
```bash
# Test individual agents
cd backend/agents/analyze-agent
python -m pytest tests/

# Test Observer service
python -m pytest observer_tests.py

# Test data pipeline with mock data
python test_pipeline.py --use-mock-data

# Test conversational agent
cd conv_agent_vertex
pytest tests/test_agents.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the logs in Google Cloud Console for debugging
- Review Firestore data for processing status

## 🔮 Future Enhancements

### Technical Roadmap
- **Real-time WebSocket connections** for live city pulse updates
- **Advanced ML models** for better event prediction and trend forecasting
- **Mobile application** with push notifications and offline capabilities
- **Advanced analytics dashboard** with interactive visualizations
- **Multi-city support** with region-specific agents and cultural adaptations

### AI & Intelligence Improvements
- **Enhanced NLP models** for better content understanding and categorization
- **Predictive analytics** for forecasting city events and trends
- **Computer vision integration** for processing image/video content from social media
- **Voice interface** for hands-free city information access
- **Automated content verification** to combat misinformation

### Scale & Performance
- **Global deployment** with CDN integration for faster access
- **Edge computing** for reduced latency in data processing
- **Advanced caching strategies** for frequently accessed insights
- **Microservices optimization** for better resource utilization

### User Experience
- **AR/VR interfaces** for immersive city exploration
- **Collaborative features** for community-driven content validation
- **Accessibility improvements** for inclusive user access
- **Multilingual support** for diverse urban populations

---

**NagarPravah: Transforming urban noise into actionable intelligence, one data point at a time.**
