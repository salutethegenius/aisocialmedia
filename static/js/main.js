document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const editButtons = document.querySelectorAll('.edit-content');
    const scheduleButtons = document.querySelectorAll('.schedule-post');
    const editModal = document.getElementById('edit-modal');
    const scheduleModal = document.getElementById('schedule-modal');
    const editContentText = document.getElementById('edit-content-text');
    const updateContentBtn = document.getElementById('update-content');
    const closeModalBtn = document.getElementById('close-modal');
    const closeScheduleModalBtn = document.getElementById('close-schedule-modal');
    const scheduleForm = document.getElementById('schedule-form');
    const scheduledPostsList = document.getElementById('scheduled-posts-list');

    let currentContentId = null;

    if (sendButton && userInput) {
        sendButton.addEventListener('click', () => generateContent());
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                generateContent();
            }
        });
    }

    async function generateContent() {
        const topic = userInput.value.trim();
        if (!topic) return;

        addMessage('user', topic);
        userInput.value = '';

        try {
            const response = await fetch('/generate_content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic, tone: 'informative' }),
            });

            if (response.ok) {
                const data = await response.json();
                addMessage('bot', data.content);
                currentContentId = data.id;
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'An error occurred while generating content');
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('error', 'An error occurred while generating content: ' + error.message);
        }
    }

    function addMessage(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    editButtons.forEach(button => {
        button.addEventListener('click', () => {
            currentContentId = button.dataset.id;
            const content = button.parentElement.querySelector('p').textContent;
            editContentText.value = content;
            editModal.style.display = 'block';
        });
    });

    scheduleButtons.forEach(button => {
        button.addEventListener('click', () => {
            currentContentId = button.dataset.id;
            document.getElementById('schedule-content-id').value = currentContentId;
            scheduleModal.style.display = 'block';
        });
    });

    if (updateContentBtn) {
        updateContentBtn.addEventListener('click', async () => {
            const updatedContent = editContentText.value;

            try {
                const response = await fetch('/update_content', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ id: currentContentId, content: updatedContent }),
                });

                if (response.ok) {
                    editModal.style.display = 'none';
                    location.reload();
                } else {
                    const error = await response.json();
                    throw new Error(error.error || 'An error occurred while updating content');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while updating content: ' + error.message);
            }
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            editModal.style.display = 'none';
        });
    }

    if (closeScheduleModalBtn) {
        closeScheduleModalBtn.addEventListener('click', () => {
            scheduleModal.style.display = 'none';
        });
    }

    if (scheduleForm) {
        scheduleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const contentId = document.getElementById('schedule-content-id').value;
            const scheduledTime = document.getElementById('schedule-time').value;
            const platform = document.getElementById('schedule-platform').value;

            try {
                console.log('Sending schedule post request:', { content_id: contentId, scheduled_time: scheduledTime, platform });
                const response = await fetch('/schedule_post', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ content_id: contentId, scheduled_time: scheduledTime, platform }),
                });

                console.log('Schedule post response:', response);
                const responseData = await response.json();
                console.log('Schedule post response data:', responseData);

                if (response.ok) {
                    if (responseData.redirect) {
                        window.location.href = responseData.redirect;
                    } else {
                        scheduleModal.style.display = 'none';
                        loadScheduledPosts();
                    }
                } else {
                    throw new Error(responseData.error || 'Failed to schedule post');
                }
            } catch (error) {
                console.error('Error scheduling post:', error);
                alert('An error occurred while scheduling the post: ' + error.message);
            }
        });
    }

    async function loadScheduledPosts() {
        if (!scheduledPostsList) {
            console.log('Scheduled posts list not found on this page');
            return;
        }
        try {
            const response = await fetch('/get_scheduled_posts');
            if (response.ok) {
                const posts = await response.json();
                scheduledPostsList.innerHTML = '';
                posts.forEach(post => {
                    const li = document.createElement('li');
                    li.textContent = `Topic: ${post.topic}, Scheduled for: ${new Date(post.scheduled_time).toLocaleString()}, Platform: ${post.platform}, Status: ${post.status}`;
                    scheduledPostsList.appendChild(li);
                });
            } else {
                throw new Error('Failed to load scheduled posts');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while loading scheduled posts: ' + error.message);
        }
    }

    loadScheduledPosts();

    window.addEventListener('click', (event) => {
        if (event.target === editModal) {
            editModal.style.display = 'none';
        }
        if (event.target === scheduleModal) {
            scheduleModal.style.display = 'none';
        }
    });
});
