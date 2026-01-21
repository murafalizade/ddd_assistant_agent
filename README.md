# Project title: AI system for Structuring, and Querying of Daily Drilling Reports (DDRs)

## 1. Objective
The objective of this project is to design, develop, and deploy an AI-based system that automatically reads, understands, and summarizes technical Daily Drilling Reports (DDRs). The system will detect anomalies, patterns, and operational trends by combining:  
- Document-level Computer Vision (Vision-Language Models / OCR)  
- Domain-specific Natural Language Processing (NLP)  
- Structured Databases and Intelligent Querying  
- LLM-powered Question Answering via a Chatbot Interface  

The final system will be deployed as a web application using Streamlit for demonstration purposes.

## 2. System Architecture Overview
The overall AI system consists of three main components:  
- Input & Document Processing Layer (Vision + OCR)  
- NLP & Analytics Layer  
- Chatbot & User Interaction Layer  

## 3. Vision Model (Document Processing)
Train/Customize/Use a vision model to:  
- Parse the structure of DDRs automatically (detect sections, tables, plots).  
- Extract numeric and tabular data from text and images using OCR and image processing.  
- Save extracted data into an SQL database.  

## 4. NLP Model (Understanding & Analytics)
Develop NLP model to:  
- Detect events and classify them (e.g., drilling, reaming, etc.), as well as possible anomalies  
- Create Daily Short Summary  
- Parameters extraction and trend analysis (Build a structured time-series database across multiple days.)  

## 5. Chatbot System (Question Answering)
Chatbot system should:  
- Use retrieval methods to query structured data from the database.  
- Answer user questions based on extracted tables and text.  
- Describe pressure plots using image processing and VLM (or other pre-training models) in chatbot.  

## 6. Technologies & Research Topics
You can search for the following topics to improve system:  
- RAG  
- TAG  
- Text2SQL  
- Multi-Agent Systems  
- Vision-Language Models (VLMs)  
- OCR and Document AI  
- Image Processing for Plot Interpretation  
- LLM-based chatbot systems (e.g., Gemini, local LLMs)  

## 7. Deployment
- The complete system will be deployed using Streamlit (https://streamlit.io/) as an interactive web application.  
- After a DDR is uploaded, it is automatically processed and stored in a central database together with all previous DDRs.  
- A chat interface allows users to ask questions and receive explanations of plots and images.  
- The application provides visualization of trends and detected anomalies across all stored reports.
