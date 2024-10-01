document.addEventListener('DOMContentLoaded', () => {
    const generateForm = document.getElementById('generate-form');
    const generatedContent = document.getElementById('generated-content');
    const contentText = document.getElementById('content-text');
    const tokensUsed = document.getElementById('tokens-used');
    const saveContentBtn = document.getElementById('save-content');
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

    if (generateForm) {
        generateForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const topic = document.getElementById('topic').value;
            const tone = document.getElementById('tone').value;

            try {
                const response = await fetch('/generate_content', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ topic, tone }),
                });

                if (response.ok) {
                    const data = await response.json();
                    contentText.value = data.content;
                    tokensUsed.textContent = data.tokens_used;
                    currentContentId = data.id;
                    generatedContent.style.display = 'block';
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'An error occurred while generating content');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while generating content: ' + error.message);
            }
        });
    }

    if (saveContentBtn) {
        saveContentBtn.addEventListener('click', () => {
            location.reload();
        });
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
                const response = await fetch('/schedule_post', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ content_id: contentId, scheduled_time: scheduledTime, platform }),
                });

                if (response.ok) {
                    window.location.href = response.url;
                } else {
                    throw new Error('Failed to schedule post');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while scheduling the post: ' + error.message);
            }
        });
    }

    async function loadScheduledPosts() {
        const scheduledPostsList = document.getElementById('scheduled-posts-list');
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
                    li.textContent = `Content ID: ${post.content_id}, Scheduled for: ${new Date(post.scheduled_time).toLocaleString()}, Platform: ${post.platform}, Status: ${post.status}`;
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