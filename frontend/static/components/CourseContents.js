import Navbar from "/static/components/Navbar.js"

export default {
    template: `
    <Navbar @toggle-chatbot="toggleChatbot">
        <div class="row" style="width:100%">
            <div class="col-2" style="width: 20%; padding-right: 0px;">
                <div style="margin-left:5%"> 
                <h4 style="color: #015668;margin-top: 30px;margin-bottom: 30px;text-align:center">Course Contents</h4>
                <div class="accordion" id="accordion">
                    <div class="accordion-item" v-for="weeknumber in weeks" :key="weeknumber">
                            <h2 class="accordion-header" :id="'heading' + weeknumber">
                                <button class="accordion-button" type="button" 
                                        :data-bs-toggle="'collapse'"
                                        :class="{ 'collapsed': activeWeek !== weeknumber }"
                                        :data-bs-target="'#collapse' + weeknumber" 
                                        :aria-expanded="activeWeek === weeknumber"
                                        :aria-controls="'collapse' + weeknumber"
                                        @click="activeWeek = activeWeek === weeknumber ? -1 : weeknumber">
                                    Week {{ weeknumber }}
                                </button>
                            </h2>
                            <div class="accordion-collapse collapse" 
                                :class="{ 'show': activeWeek === weeknumber }"
                                :id="'collapse' + weeknumber"
                                data-bs-parent="#accordion">
                               <div class="accordion-body" :style="{ padding: '0' }">
                                    <ul class="list-group" :style="{ margin: '0', borderRadius: '0' }">
                                        <li class="list-group-item"
                                            v-for="lecture in sortedLectures(weeknumber)" 
                                            :key="lecture.lecturenumber"
                                            :style="{
                                                height: '65px', 
                                                display: 'flex', 
                                                alignItems: 'center', 
                                                margin: '0',
                                                backgroundColor: selectedLectureNumber === lecture.lecturenumber ? '#f8f1e4' : 'white', 
                                                fontWeight: selectedLectureNumber === lecture.lecturenumber ? 'bold' : 'normal',
                                                cursor: 'pointer'
                                            }"
                                            @click="playLecture(lecture.link, lecture.title, lecture.lecturenumber)">
                                            
                                            <a href="#" @click.prevent
                                                :style="{ display: 'flex', alignItems: 'center', width: '100%', height: '100%', textDecoration: 'none', color: 'inherit' }">
                                                L{{ lecture.lecturenumber }} {{ lecture.title }}
                                            </a>
                                        </li>
                                        <li class="list-group-item"
                                            :style="{
                                                height: '65px', 
                                                display: 'flex', 
                                                alignItems: 'center', 
                                                margin: '0',
                                                backgroundColor: selectedMock === weeknumber ? '#f8f1e4' : 'white', 
                                                fontWeight: selectedMock === weeknumber ? 'bold' : 'normal',
                                                cursor: 'pointer'
                                            }"
                                            @click="fetchMockQns(weeknumber)">
                                            <a :style="{ display: 'flex', alignItems: 'center', width: '100%', height: '100%', textDecoration: 'none', color: 'inherit' }">
                                                Mock Questions
                                            </a>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                </div>
            </div>
            </div>

            <!-- Main Content Area -->
            <div class="col-10" style="width: 80%; padding: 20px;">
                <!-- Video Player -->
                <div v-if="selectedLecture && !showChatbot" class="video-container" style="text-align: center;">
                    <h4 style="color: #015668; margin-bottom: 20px;">Lecture {{ selectedLectureNumber }}: {{ selectedLectureTitle }}</h4>
                    <iframe 
                        :src="selectedLecture"
                        style="width: 80%; height: 500px; border: none;"
                        allowfullscreen>
                    </iframe>
                </div>
                
                <!-- Mock Questions Display -->
                <div v-if="selectedMock && !showChatbot" style="text-align: left; max-width: 800px; margin: 0 auto;">
                    <div style="background-color: #015668; border-radius: 10px; padding: 15px; margin-bottom: 30px; color: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                        <h4 style="margin-bottom: 10px; color: white; font-weight: 600;">Mock Questions - Week {{ selectedMock }}</h4>
                        <p style="margin-bottom: 0; font-size: 14px;">Questions are generated randomly. You can attempt any number of times. This assignment is for your practice.</p>
                    </div>
                    
                    <!-- Loading indicator for mock questions -->
                    <div v-if="mcqsLoading" class="loading-container" style="text-align: center; margin: 50px 0;">
                        <div class="spinner" style="display: inline-block; border: 4px solid #f3f3f3; border-top: 4px solid #015668; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
                        <p style="margin-top: 15px; color: #015668; font-weight: 500;">Loading questions...</p>
                    </div>

                    <!-- Demo Mode notice when AI is unavailable -->
                    <div v-if="aiUnavailable && !mcqsLoading" style="text-align: center; margin: 40px auto; max-width: 500px; padding: 24px; background: #fff8e1; border: 1px solid #ffe082; border-radius: 12px;">
                        <div style="font-size: 32px; margin-bottom: 12px;">🚧</div>
                        <h5 style="color: #e65100; margin-bottom: 8px;">Demo Mode — AI Disabled</h5>
                        <p style="color: #555; font-size: 14px; margin: 0;">
                            The AI-powered mock questions are not available in this hosted demo due to some constraints.<br><br>
                            <strong>The complete version runs locally.</strong>
                        </p>
                    </div>

                    
                    <div v-else-if="mcqs.length > 0" class="questions-container" style="margin-bottom: 30px;">
                        <div v-for="(question, index) in mcqs" :key="index" class="question-block" style="background-color: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); padding: 20px; margin-bottom: 25px;">
                            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                                <div style="width: 32px; height: 32px; border-radius: 50%; background-color: #015668; color: white; display: flex; justify-content: center; align-items: center; margin-right: 12px; font-weight: 600;">
                                    {{ index + 1 }}
                                </div>
                                <h5 style="margin: 0; font-weight: 500; color: #333; flex-grow: 1;">{{ question.question_statement }}</h5>
                            </div>
                            
                            <div class="options" style="margin-left: 44px;">
                                <div v-for="(option, optionKey) in ['A', 'B', 'C', 'D']" :key="optionKey" 
                                    class="option-item" 
                                    style="padding: 12px; border-radius: 8px; margin-bottom: 10px; cursor: pointer; transition: all 0.2s;"
                                    :style="{ 
                                        backgroundColor: userAnswers[index] === option ? '#e1f5fe' : '#f8f9fa',
                                        border: userAnswers[index] === option ? '2px solid #4fc3f7' : '2px solid transparent'
                                    }"
                                    @click="userAnswers[index] = option">
                                    
                                    <label style="display: flex; align-items: center; width: 100%; cursor: pointer; margin: 0;">
                                        <div style="display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; border: 2px solid #015668; margin-right: 10px; flex-shrink: 0;">
                                            <div v-if="userAnswers[index] === option" style="width: 12px; height: 12px; border-radius: 50%; background-color: #015668;"></div>
                                        </div>
                                        <span style="flex-grow: 1; font-size: 15px;">
                                            <strong>Option {{ option }}:</strong> {{ question['option_' + option.toLowerCase()] }}
                                        </span>
                                        <input type="radio" :name="'question-' + index" :value="option" v-model="userAnswers[index]" style="display: none;" />
                                    </label>
                                </div>
                            </div>
                        </div>
                        
                        <button @click="checkAnswers" 
                                class="submit-button" 
                                style="background-color: #015668; color: white; padding: 12px 25px; border: none; border-radius: 25px; font-size: 16px; font-weight: 500; cursor: pointer; display: block; margin: 30px auto; box-shadow: 0 3px 5px rgba(0,0,0,0.2); transition: all 0.2s;"
                                :style="{ opacity: userAnswers.length > 0 ? '1' : '0.7' }"
                                :disabled="userAnswers.length === 0">
                            Check Answers
                        </button>
                    </div>

                    <!-- Results Section - Keeping the previously enhanced version -->
                    <div v-if="showResults" class="results-container" style="margin-top: 30px; padding: 20px; border-radius: 10px; background-color: #f5f5f5;">
                        <h3 style="color: #015668; margin-bottom: 20px;">Your Results:</h3>
                        
                        <div v-for="(result, index) in results" :key="index" class="result-item" 
                            style="margin-bottom: 15px; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);"
                            :style="{ backgroundColor: result.isCorrect ? '#e8f5e9' : '#ffebee' }">
                            
                            <h5 style="margin-bottom: 10px;">Question {{ index + 1 }}</h5>
                            
                            <div style="display: flex; align-items: flex-start;">
                                <div style="width: 30px; height: 30px; border-radius: 50%; display: flex; justify-content: center; align-items: center; margin-right: 10px;"
                                    :style="{ backgroundColor: result.isCorrect ? '#4caf50' : '#f44336', color: 'white' }">
                                    <span v-if="result.isCorrect">✓</span>
                                    <span v-else>✗</span>
                                </div>
                                
                                <div style="flex-grow: 1;">
                                    <p style="margin-bottom: 8px; font-weight: 500;">
                                        <span v-if="result.isCorrect">Correct!</span>
                                        <span v-else>Incorrect</span>
                                    </p>
                                    
                                    <div style="margin-bottom: 5px;">
                                        <strong>Your answer:</strong> Option {{ result.userAnswer }} - {{ result.userOptionText }}
                                    </div>
                                    
                                    <div>
                                        <strong>Correct answer:</strong> Option {{ result.correctAnswer }} - {{ result.correctOptionText }}
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Summary section -->
                        <div style="margin-top: 20px; padding: 15px; border-radius: 8px; background-color: #e1f5fe; text-align: center;">
                            <h4 style="margin-bottom: 10px;">Summary</h4>
                            <p style="font-size: 18px; font-weight: 500;">
                                You got {{ results.filter(r => r.isCorrect).length }} out of {{ results.length }} questions correct
                                ({{ Math.round((results.filter(r => r.isCorrect).length / results.length) * 100) }}%)
                            </p>
                        </div>
                        
                        <div style="margin-top: 20px; text-align: center;">
                            <button @click="fetchMockQns(selectedMock)" class="btn" 
                                    style="background-color: #015668; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                                Try Again with New Questions
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Ask Lumi Chat Interface -->
                <div v-if="showChatbot" class="chat-container" style="height: 600px; display: flex; flex-direction: column;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h4 style="color: #015668; margin: 0;">Ask Lumi</h4>
                        <button 
                            @click="startNewChat" 
                            class="btn" 
                            style="background-color: #015668; color: white; padding: 5px 10px; font-size: 14px;"
                        >
                            New Chat
                        </button>
                    </div>
                    
                    <!-- Chat messages display area -->
                    <div class="chat-messages" style="flex: 1; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 5px; padding: 15px; margin-bottom: 15px; background-color: #f9f9f9;">
                        <div v-for="(message, index) in chatMessages" :key="index" class="message" :style="{
                            textAlign: message.sender === 'user' ? 'right' : 'left',
                            marginBottom: '15px'
                        }">
                            <div :style="{
                                display: 'inline-block',
                                padding: '10px 15px',
                                borderRadius: '10px',
                                maxWidth: '70%',
                                backgroundColor: message.sender === 'user' ? '#e1f5fe' : '#e8f5e9',
                                color: '#333333',
                                textAlign: 'left'  // This is the new style property
                            }">
                                <strong>{{ message.sender === 'user' ? 'You' : 'Lumi' }}:</strong> {{ message.text }}
                            </div>
                        </div>
                        <!-- Loading indicator for chat -->
                        <div v-if="isLoadingResponse" class="message" style="text-align: left; marginBottom: '15px'">
                            <div style="
                                display: inline-block;
                                padding: 10px 15px;
                                borderRadius: 10px;
                                backgroundColor: #e8f5e9;
                                color: #333333;
                                textAlign: left
                            ">
                                <strong>Lumi:</strong> 
                                <span class="loading-dots">Loading<span>.</span><span>.</span><span>.</span></span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Input area -->
                    <div class="chat-input" style="display: flex; gap: 10px;">
                        <textarea 
                            v-model="query" 
                            placeholder="Ask something..." 
                            class="form-control" 
                            style="resize: none; height: 80px;"
                            @keyup.enter="askLumi"
                            :disabled="isLoadingResponse"
                        ></textarea>
                        <button 
                            @click="askLumi" 
                            class="btn" 
                            style="background-color: #015668; color: white; align-self: flex-end; height: 40px; width: 100px;"
                            :disabled="isLoadingResponse"
                        >
                            Send
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </Navbar>
    `,
    components:{
        Navbar
    },
    data() {
        return {
            token: JSON.parse(localStorage.getItem('user')).token,
            user_id: JSON.parse(localStorage.getItem('user')).id,
            user_name: JSON.parse(localStorage.getItem('user')).name,
            id: this.$route.query.id,
            error: null,
            weeks: [],
            activeWeek: 1, // Tracks which week content is open by default
            openingWeek: null,
            lectures: [],
            selectedLecture: null, // Stores the selected lecture video link
            selectedLectureTitle: "",  // Store the selected lecture title
            selectedLectureNumber: null, // Track selected lecture
            selectedMock: null, // Track selected Mock,
            mcqsLoading: false,
            mcqs: [],
            userAnswers: [],
            showResults: false,
            results: [],
            showChatbot: false, // Toggle Ask Lumi
            query: "",
            aiUnavailable: false, // Set to true when backend reports AI features unavailable
            isLoadingResponse: false, // New flag for chat loading indicator
            chatMessages: [
                { sender: 'lumi', text: 'Hi there! I\'m Lumi, your learning assistant. How can I help you today?' }
            ], // Array to store chat messages for display
            chatHistory: [] // Array to store chat history for AI context
        }
    },
    created(){
        this.fetchLectures()
        // Add CSS for loading animation
        this.addLoadingAnimations()
    },
    mounted() {
        // Wait for lectures to be fetched before selecting default
        this.fetchLectures().then(() => {
            if (this.lectures.length > 0) {
                let firstWeek = Math.min(...this.weeks); // Get the first available week
                this.openingWeek = firstWeek; // Open first week
                
                let firstLecture = this.sortedLectures(firstWeek)[0]; // Get first lecture
                if (firstLecture) {
                    this.playLecture(firstLecture.link, firstLecture.title, firstLecture.lecturenumber);
                }
            }
        });
    },
    methods: {
        addLoadingAnimations() {
            // Add CSS for animations to document head
            const style = document.createElement('style');
            style.innerHTML = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                @keyframes blink {
                    0% { opacity: 0.2; }
                    20% { opacity: 1; }
                    100% { opacity: 0.2; }
                }
                
                .loading-dots span {
                    animation: blink 1.4s infinite;
                    animation-fill-mode: both;
                }
                
                .loading-dots span:nth-child(2) {
                    animation-delay: 0.2s;
                }
                
                .loading-dots span:nth-child(3) {
                    animation-delay: 0.4s;
                }
            `;
            document.head.appendChild(style);
        },
        clearMessage() {
            this.error = null
        },
        async fetchLectures(){
            const res = await fetch(`/get_all_lectures/${this.id}`, {
                headers: {
                    "Authentication-Token": this.token
                }
            })

            if (res.ok) {
                const data = await res.json()
                this.lectures = data
                this.weeks = new Set([...this.lectures
                    .map(lecture => lecture.weeknumber) // Extract week numbers
                    .sort((a, b) => a - b) // Sort in ascending order
                  ]);
            }
        },
        toggleAccordion(index) {
            this.activeIndex = this.activeIndex === index ? null : index;
        },
        sortedLectures(week) {
            return this.lectures
              .filter(lecture => lecture.weeknumber === week)
              .sort((a, b) => a.lecturenumber - b.lecturenumber);
        },
        playLecture(link, video_title, lecturenumber) {
            // Turn off chatbot if it's active
            this.showChatbot = false;
            
            //Clear Mock questions selection
            this.selectedMock = null 
            this.userAnswers=[],
            this.showResults=false,
            this.results=[]
            this.mcqs=[]

            // Convert youtu.be link to embed format
            if (link.includes("youtu.be/")) {
                let videoId = link.split("youtu.be/")[1]; // Extract video ID
                this.selectedLecture = `https://www.youtube.com/embed/${videoId}`;
                this.selectedLectureTitle = video_title;
                this.selectedLectureNumber = lecturenumber; 
            } else {
                this.selectedLecture = link; // Use the same link if it's already an embed link
                this.selectedLectureTitle = video_title;
                this.selectedLectureNumber = lecturenumber; 
            }
        },
        async fetchMockQns(week){
            // Turn off chatbot if it's active
            this.showChatbot = false;
            
            this.selectedMock = week

            // Clear previous mock selection
            this.userAnswers = [];
            this.showResults = false;
            this.results = [];
            this.mcqs = [];
            
            // Clear lecture selection
            this.selectedLecture = null;
            this.selectedLectureTitle = "";
            this.selectedLectureNumber = null;

            // Show loading indicator
            this.mcqsLoading = true;

            const res = await fetch(`/mock?week=${week}&num_questions=3`, {
                headers: {
                    "Authentication-Token": this.token
                }
            });
            
            if (res.ok) {
                const data = await res.json();
                // Check if backend returned an AI-unavailable error
                if (data.mcqs && data.mcqs.error) {
                    this.aiUnavailable = true;
                    this.mcqs = [];
                } else {
                    this.mcqs = data.mcqs;
                }
            }
            
            // Hide loading indicator
            this.mcqsLoading = false;
        },
        checkAnswers() {
            this.results = this.mcqs.map((question, index) => {
                const userAnswer = this.userAnswers[index];
                const correctAnswer = question.correct_answer;
                const isCorrect = userAnswer === correctAnswer;
                
                // Get the text content of the selected option and correct option
                const getUserOptionText = (optionLetter) => {
                    switch(optionLetter) {
                        case 'A': return question.option_a;
                        case 'B': return question.option_b;
                        case 'C': return question.option_c;
                        case 'D': return question.option_d;
                        default: return '';
                    }
                };
                
                const userOptionText = userAnswer ? getUserOptionText(userAnswer) : 'No answer selected';
                const correctOptionText = getUserOptionText(correctAnswer);
                
                return {
                    isCorrect: isCorrect,
                    userAnswer: userAnswer || 'None',
                    correctAnswer: correctAnswer,
                    userOptionText: userOptionText,
                    correctOptionText: correctOptionText
                };
            });
            
            this.showResults = true;
        },
        toggleChatbot() {
            // This method is triggered from the Navbar component
            this.showChatbot = true;
            
            // Clear other content
            this.selectedLecture = null;
            this.selectedMock = null;
            this.selectedLectureTitle = "";
            this.selectedLectureNumber = null;
            this.mcqs = [];
        },
        startNewChat() {
            // Reset the chat to initial state
            this.chatMessages = [
                { sender: 'lumi', text: 'Hi there! I\'m Lumi, your learning assistant. How can I help you today?' }
            ];
            
            // Clear the chat history for AI context
            this.chatHistory = [];
            
            // Clear the query field
            this.query = "";
        },
        async askLumi() {
            if (!this.query.trim() || this.isLoadingResponse) return; // Prevent empty messages or submissions while loading

            // Add user message to chat display
            this.chatMessages.push({
                sender: 'user',
                text: this.query
            });
            
            const currentQuery = this.query;
            this.query = ""; // Clear input field immediately
            
            // Show loading indicator
            this.isLoadingResponse = true;
            
            try {
                // Prepare the chat history in the format expected by the model
                const formattedChatHistory = this.chatHistory.map(entry => ({
                    role: entry.sender === 'user' ? 'user' : 'assistant',
                    content: entry.text
                }));
                
                // Call the /mock route with POST method
                const res = await fetch("/chat", {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "Authentication-Token": this.token
                    },
                    body: JSON.stringify({ 
                        message: currentQuery,
                        chat_history: formattedChatHistory
                    })
                });
                
                if (res.ok) {
                    const data = await res.json();
                    
                    // Check if AI features are unavailable in this deployment
                    if (data.error && data.error.includes('not available')) {
                        this.aiUnavailable = true;
                        this.chatMessages.push({
                            sender: 'lumi',
                            text: '🚧 The AI assistant is not available in this demo deployment. The full version with Lumi runs locally with the complete ML stack.'
                        });
                    } else {
                        // Add AI's response to chat display
                        const aiResponse = data.response || "I'm sorry, I couldn't process your request.";
                        this.chatMessages.push({
                            sender: 'lumi',
                            text: aiResponse
                        });
                        
                        // Update chat history for context in future requests
                        this.chatHistory.push({
                            sender: 'user',
                            text: currentQuery
                        });
                        
                        this.chatHistory.push({
                            sender: 'assistant',
                            text: aiResponse
                        });
                    }
                } else {
                    // Handle error
                    this.chatMessages.push({
                        sender: 'lumi',
                        text: "Sorry, there was an error processing your request."
                    });
                }
            } catch (error) {
                console.error("Error while asking Lumi:", error);
                this.chatMessages.push({
                    sender: 'lumi',
                    text: "Sorry, there was a technical issue. Please try again later."
                });
            } finally {
                // Hide loading indicator
                this.isLoadingResponse = false;
            }
            
            // Scroll to bottom of chat after adding new messages
            this.$nextTick(() => {
                const chatContainer = document.querySelector('.chat-messages');
                if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            });
        }
    }
}
