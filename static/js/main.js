document.addEventListener('DOMContentLoaded', () => {
    const generateForm = document.getElementById('generate-form');
    const generatedContent = document.getElementById('generated-content');
    const contentText = document.getElementById('content-text');
    const tokensUsed = document.getElementById('tokens-used');
    const saveContentBtn = document.getElementById('save-content');
    const editButtons = document.querySelectorAll('.edit-content');
    const editModal = document.getElementById('edit-modal');
    const editContentText = document.getElementById('edit-content-text');
    const updateContentBtn = document.getElementById('update-content');
    const closeModalBtn = document.getElementById('close-modal');

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
                    const error = await response.json();
                    alert(`Error: ${error.error}`);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while generating content.');
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
                    alert(`Error: ${error.error}`);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while updating content.');
            }
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            editModal.style.display = 'none';
        });
    }

    window.addEventListener('click', (event) => {
        if (event.target === editModal) {
            editModal.style.display = 'none';
        }
    });
});
