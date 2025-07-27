# **App Name**: Nagar Pravah: City Insights

## Core Features:

- Data Synthesis: AI-powered synthesis of real-time city data into meaningful narratives using a team of AI agents as tool.
- Story Feed: Real-time display of synthesized events and stories on the home screen via custom-designed cards in a vertically scrolling list, with filters for Trending, Overall, and Personalization. For Trending consider top 5 events from synthesized-events which having priorityScore & mentionCount high. For Overall consider all events in synthesized-events and for personalization fetch from user-synthesized-events collection for given userId.
- City Pulse Map: Interactive city map displaying real-time data points using custom markers, pop-up summaries, and multiple map views (Mood, Events, Traffic, Overall), updated upon Firestore data ingestion in map-data collection
- Authentication: User authentication via email/password and Google Sign-In, with Firebase Authentication and Riverpod for user state management.
- Conversation Module Text input: A conversational chat interface to be primary user interaction point which can accepts input as Text (On submit, POSTs the text to the `conversational-agent` API).
- Conversation Module Voice input: A conversational chat interface to be primary user interaction point which can accepts Voice Input (uses the `speech_to_text` API package. On voice end, POSTs the transcribed text).
- Conversation Module Voice Output: A conversational chat interface to be primary user interaction point which can generates voice output with received audio stream from the API using `just_audio`.
- User Report Screen: Allow users to submit their own observations via a Form containing a TextField, a DropdownButton, and a map view for location selection. On submit, it POSTs the data to the `user-report-endpoint`.
- User Profile & Preferences: Allow users to manage personalization settings via TextFields for display_name, toggle buttons for interests, and a map interface to set home_location and work_location, using Riverpod to read/write to the user's document in user-profiles.

## Style Guidelines:

- Primary color: Deep indigo (#3F51B5) to convey intelligence and urban sophistication.
- Background color: Very light gray (#F5F5F5) for the light theme and dark gray (#303030) for the dark theme.
- Accent color: Teal (#009688) to highlight key interactive elements and call attention to real-time updates.
- Headline font: 'Poppins' (sans-serif) for headlines; body font: 'PT Sans' (sans-serif) for a readable and modern text.
- Custom-designed icon pack that complements the modern and trendy theme.
- Clean and minimalist layout with subtle neumorphic or glassmorphic design elements for key cards and buttons.
- Smooth animations and transitions between screens to enhance user experience.