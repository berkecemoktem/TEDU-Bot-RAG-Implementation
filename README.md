## Purpose
The purpose of this project is to develop a chatbot system for TED University (TEDU) to assist
students, staff, and prospective students. Using LLM grounding techniques, the chatbot will
provide accurate, context-specific responses based on TEDU's introduction booklet, website, and
FAQs. This system aims to enhance user experience by facilitating learning, teaching, and
activity management within TEDU. 

## How does it work briefly?
The chatbot system comprises three agents:
1. Intent Manager Agent: Directs users to the appropriate agent based on their queries.
2. TEDU Assistant: Answers FAQs related to TEDU policies, events, facilities, and general
information.
3. Course Suggestion Chatbot: Recommends courses to students based on their
preferences, academic history, and career goals. 

## System Design:
![image](https://github.com/user-attachments/assets/635c35ea-e035-4af8-97f5-40135fbd04d0)

### Login Page:
![image](https://github.com/user-attachments/assets/8ed2cc07-f8c7-4718-a454-611a6f9d366f)

### Chatbot Screen:
![image](https://github.com/user-attachments/assets/c6ef6afc-14ec-43fd-89b1-d98fe97863a4)

### Intent identified, TEDU Assistant triggered:
![image](https://github.com/user-attachments/assets/e081b44b-d272-4a51-8b43-0b7b6de5a09e)

### Intent identified, Course Suggestion Agent triggered:

![image](https://github.com/user-attachments/assets/33e93577-f2ee-4607-ba90-fed954b466af)

### Suggestions are ready in a popup, where the student can drop ones that he/she doesn't like:
![image](https://github.com/user-attachments/assets/02494514-7c40-45a5-81cc-76735c14c81c)

## What can be improved?
- As this project is only a demonstration of a RAG implementation and uses a small amount of data, some of the queries are not found in the dataset. Therefore, numerically more and more organized data will enhance the performance of the system.
- Also, note that these system prompts are open to be improved by using the prompt engineering techniques. A better prompts will result in a higher accuracy in terms of LLM responses. 
- Lastly, as these kind of applications require the updated data (like when the number of students increase, system should answer with the updated data), adapting a dynamic approach such as using an api to collect the up to date data (about the university rules, course information, exam dates etc.) would be crucial in a real life scenario 
