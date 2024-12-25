
const API_URL = 'http://127.0.0.1:5000/api/chat';
const GOOGLE_API_KEY = 'AIzaSyDtbAdzBiBgHxr_AUSZUfUD-x_cSZMikcw';

const temperatureSlider = document.getElementById("temperature-slider");
const temperatureValue = document.getElementById("temperature-value");

// Initialize or retrieve users from localStorage
const users = JSON.parse(localStorage.getItem("users")) || [];

// Login Functionality
document.getElementById("login-form")?.addEventListener("submit", function (e) {
    e.preventDefault();
    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value.trim();

    const user = users.find((user) => user.username === username && user.password === password);

    if (user) {
        alert("Login successful!");
        window.location.href = "homepage.html"; // Redirect to homepage
    } else {
        alert("Invalid username or password.");
    }
});

// Signup Functionality
document.getElementById("signup-form")?.addEventListener("submit", function (e) {
    e.preventDefault();
    const username = document.getElementById("signup-username").value.trim();
    const password = document.getElementById("signup-password").value.trim();

    // Check if username already exists
    const userExists = users.some((user) => user.username === username);

    if (userExists) {
        alert("Username already taken. Please choose a different one.");
        return;
    }

    // Add user to the array and save in localStorage
    users.push({ username, password });
    localStorage.setItem("users", JSON.stringify(users));

    alert("Signup successful! Please log in.");
    window.location.href = "index.html"; // Redirect to login page
});

// Preferences Functionality
document.getElementById("preferences-form")?.addEventListener("submit", function (e) {
    e.preventDefault();
    const preference = document.getElementById("preference-input").value.trim();

    alert(`Preference saved: ${preference}`);
    // Optionally, save preferences in localStorage
    localStorage.setItem("preference", preference);
});

// Chatbot interaction
/*document.getElementById("chat-form")?.addEventListener("submit", async function (e) {
    e.preventDefault();
    
    const chatInput = document.getElementById("chat-input");
    const chatDisplay = document.getElementById("chat-display");
    
    const userMessage = chatInput.value.trim();
    if (!userMessage) return;

    // Display user message
    const userBubble = document.createElement("div");
    userBubble.className = "message user";
    userBubble.innerText = userMessage;
    chatDisplay.appendChild(userBubble);

    // Mock LLM Response (replace with API call)
    const llmResponse = await getLLMResponse(userMessage);
    const llmBubble = document.createElement("div");
    llmBubble.className = "message llm";
    llmBubble.innerText = llmResponse;
    chatDisplay.appendChild(llmBubble);

    // Scroll to the bottom
    chatDisplay.scrollTop = chatDisplay.scrollHeight;

    // Clear input
    chatInput.value = "";
});*/

async function sendQuery(query) {
    try {
        const requestBody = {
            query: query,
            temperature: parseFloat(temperatureSlider.value), // Get temperature from slider
            academic_level: 'undergraduate',
            department: 'Engineering'
        };

        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${GOOGLE_API_KEY}`,
                'Accept': 'application/json',
                'Origin': window.location.origin
            },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status}, Response: ${errorText}`);
        }

        const responseData = await response.json();

        // Handle based on intent
        if (responseData.intent === "course_suggestion") {
            showSuggestionsPopup(responseData.recommendations);
        } else if (responseData.intent === "tedu_assistant") {
            addMessageToChat(responseData.response, "llm");
        } else {
            throw new Error("Unrecognized intent in response.");
        }
    } catch (error) {
        console.error('Error in sendQuery:', error.message);
        addMessageToChat("Sorry, something went wrong. Please try again.", "llm error");
    }
}


function addMessageToChat(message, type = "user") {
    // Select the chat display container
    const chatDisplay = document.getElementById("chat-display");

    // Create a new message bubble
    const messageBubble = document.createElement("div");
    messageBubble.className = `message ${type}`; // Add class based on message type
    messageBubble.innerText = message; // Set the message text

    // Append the message bubble to the chat display
    chatDisplay.appendChild(messageBubble);

    // Scroll to the bottom of the chat display
    chatDisplay.scrollTop = chatDisplay.scrollHeight;
}

function showSuggestionsPopup(recommendations) {
    const popup = document.getElementById("suggestions-popup");
    const container = document.getElementById("suggestions-container");

    // Clear previous content
    container.innerHTML = "";

    // Populate with new suggestions
    recommendations.forEach((rec, index) => {
        const card = document.createElement("div");
        card.className = "suggestion-card";
        card.innerHTML = `
            <h3>${rec.name} (${rec.code})</h3>
            <p>⭐ Credits: ${rec.credits}</p>
            <p>🏢 Department: ${rec.department}</p>
            <p>🔍 Description: ${rec.description}</p>
            <p>⚙️ Prerequisites: ${rec.prerequisites.join(", ")}</p>
            <p>🎯 Why this course: ${rec.relevance_explanation}</p>
            <button class="remove-button">X</button>
        `;

        // Remove card on "X" click
        card.querySelector(".remove-button").addEventListener("click", () => {
            card.remove();
        });

        container.appendChild(card);
    });

    // Show the popup
    popup.style.display = "flex";

    // Close button functionality
    document.querySelector(".close-button").addEventListener("click", () => {
        popup.style.display = "none";
    });
}




// LLM response
/* async function getLLMResponse(message) {
    try {
        // Get saved preferences from localStorage (if they exist)
        const savedDepartment = localStorage.getItem('department');
        const savedAcademicLevel = localStorage.getItem('academicLevel') || 'undergraduate';
        const savedCredits = localStorage.getItem('preferredCredits');
        const savedTemperature = localStorage.getItem('temperature') || 0.7;

        // Construct the request body with user preferences
        const requestBody = {
            query: message,
            temperature: parseFloat(savedTemperature),
            academic_level: savedAcademicLevel
        };

        // Add optional preferences if they exist
        if (savedDepartment) requestBody.department = savedDepartment;
        if (savedCredits) requestBody.preferred_credits = parseInt(savedCredits);

        const response = await fetch('http://localhost:5000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                "Authorization": `Bearer ${env.GOOGLE_API_KEY}`
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Handle different response types based on intent
        if (data.intent === "course_suggestion") {
            let formattedResponse = "📚 Course Recommendations:\n\n";
            data.recommendations.forEach((course, index) => {
                formattedResponse += `${index + 1}. ${course.name} (${course.code})\n`;
                formattedResponse += `   📝 Department: ${course.department}\n`;
                formattedResponse += `   ⭐ Credits: ${course.credits}\n`;
                if (course.prerequisites && course.prerequisites.length > 0) {
                    formattedResponse += `   ⚠️ Prerequisites: ${course.prerequisites.join(', ')}\n`;
                }
                formattedResponse += `   🎯 Why this course: ${course.relevance_explanation}\n\n`;
            });
            return formattedResponse;
        } else {
            // Return the general assistant response
            return data.response;
        }

    } catch (error) {
        console.error('Error:', error);
        if (error.message.includes('Failed to fetch')) {
            return "⚠️ Unable to connect to the server. Please check if the server is running and try again.";
        }
        return `⚠️ Error: ${error.message}`;
    }
}*/

// Update chat form event listener
document.getElementById("chat-form")?.addEventListener("submit", async function (e) {
    e.preventDefault();
    
    const chatInput = document.getElementById("chat-input");
    const chatDisplay = document.getElementById("chat-display");
    const submitButton = this.querySelector('button[type="submit"]');
    
    const userMessage = chatInput.value.trim();
    if (!userMessage) return;

    // Display user message
    const userBubble = document.createElement("div");
    userBubble.className = "message user";
    userBubble.innerText = userMessage;
    chatDisplay.appendChild(userBubble);

    // Show loading state
    submitButton.disabled = true;
    const loadingBubble = document.createElement("div");
    loadingBubble.className = "message llm loading";
    loadingBubble.innerText = "Thinking...";
    chatDisplay.appendChild(loadingBubble);

    try {
        // Get LLM Response
        const llmResponse = await sendQuery(userMessage);
        
        // Replace loading message with formatted response
        loadingBubble.className = "message llm";
        if (llmResponse.intent === "course_suggestion") {
            // Format the recommendations for display
            const formattedResponse = llmResponse.recommendations.map(rec => {
                return `📚 ${rec.name} (${rec.code})
   ⭐ Credits: ${rec.credits}
   🏢 Department: ${rec.department}
   🔍 Description: ${rec.description}
   ⚙️ Prerequisites: ${rec.prerequisites.join(', ')}
   🎯 Why this course: ${rec.relevance_explanation}`;
            }).join("\n\n");

            loadingBubble.innerText = formattedResponse;
        } else {
            loadingBubble.innerText = llmResponse.response;
        }
    } catch (error) {
        loadingBubble.className = "message llm error";
        loadingBubble.innerText = "Sorry, something went wrong. Please try again.";
    } finally {
        submitButton.disabled = false;
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
        chatInput.value = "";
    }
});

// Close popup on 'Esc' key press
document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
        const popup = document.getElementById("suggestions-popup");
        if (popup.style.display === "flex") {
            popup.style.display = "none";
        }
    }
});

// Update displayed value when slider is adjusted
temperatureSlider.addEventListener("input", function () {
    temperatureValue.textContent = this.value;
});

