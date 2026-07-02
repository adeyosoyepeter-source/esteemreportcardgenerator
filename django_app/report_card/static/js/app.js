// Upload functionality
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const termSelect = document.getElementById('id_term');
const yearInput = document.getElementById('id_year');
const uploadStatus = document.getElementById('uploadStatus');
const studentsSection = document.getElementById('studentsSection');
const studentsList = document.getElementById('studentsList');
const totalStudentsElem = document.getElementById('totalStudents');
const actionsSection = document.getElementById('actionsSection');
const individualSection = document.getElementById('individualSection');
const generateAllBtn = document.getElementById('generateAllBtn');
const generationStatus = document.getElementById('generationStatus');

let loadedStudents = [];
let allStudents = [];

function jsSanitize(name) {
    if (!name) return 'student';
    // keep alnum and replace others with underscore
    return String(name).trim().replace(/[^a-zA-Z0-9]+/g, '_').replace(/__+/g, '_').replace(/^_+|_+$/g, '') || 'student';
}

// File input handling
uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    if (!file.name.endsWith('.xlsx')) {
        showStatus('Please select an .xlsx file', 'error');
        return;
    }

    uploadFile(file);
}

function uploadFile(file) {
    if (!termSelect || !yearInput) {
        showStatus('The report details form is unavailable.', 'error');
        return;
    }

    const selectedTerm = termSelect.value;
    const enteredYear = yearInput.value.trim();

    if (!selectedTerm) {
        showStatus('Please select a term.', 'error');
        return;
    }

    if (!enteredYear) {
        showStatus('Please enter an academic year.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('term', selectedTerm);
    formData.append('year', enteredYear);

    showStatus('Uploading and processing file...', 'info');
    generateAllBtn.disabled = true;

    fetch('/api/upload/', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadedStudents = data.students || [];
            // Store all students for individual downloads
            allStudents = data.students || [];
            totalStudentsElem.textContent = data.student_count;
            // Show returned metadata so user can confirm their selection
            const metadataElem = document.getElementById('reportMetadata');
            if (metadataElem && data.report_metadata) {
                metadataElem.textContent = `Term: ${data.report_metadata.term} | Year: ${data.report_metadata.year}`;
            }
            
            displayStudents(data.students);
            displayIndividualCards(data.students);
            studentsSection.style.display = 'block';
            actionsSection.style.display = 'block';
            individualSection.style.display = 'block';
            generateAllBtn.disabled = false;
            
            showStatus(`✓ Successfully loaded ${data.student_count} students`, 'success');
        } else {
            showStatus(data.error || 'Error processing file', 'error');
            generateAllBtn.disabled = false;
        }
    })
    .catch(error => {
        showStatus(`Error: ${error.message}`, 'error');
        generateAllBtn.disabled = false;
    });
}

function displayStudents(students) {
    studentsList.innerHTML = '';
    
    students.forEach((student, index) => {
        const item = document.createElement('div');
        item.className = 'student-item';
        item.innerHTML = `
            <div class="student-info">
                <div class="student-name">${student.name}</div>
                <div class="student-meta">
                    Class: ${student.class} | Roll No: ${student.roll_no}
                </div>
            </div>
            <div class="subjects-count">${student.subjects_count} Subjects</div>
        `;
        studentsList.appendChild(item);
    });
}

function displayIndividualCards(students) {
    const individualList = document.getElementById('individualList');
    individualList.innerHTML = '';
    
    students.forEach((student, index) => {
        const card = document.createElement('div');
        card.className = 'individual-card';
        card.innerHTML = `
            <div class="card-header">${student.name}</div>
            <div class="card-details">
                <p><strong>Class:</strong> ${student.class}</p>
                <p><strong>Roll No:</strong> ${student.roll_no}</p>
                <p><strong>Subjects:</strong> ${student.subjects_count}</p>
            </div>
            <button class="card-button" onclick="downloadSinglePDF(event, ${index})">
                📄 Download PDF
            </button>
        `;
        individualList.appendChild(card);
    });
}

// Generate all PDFs
generateAllBtn.addEventListener('click', () => {
    generateAllBtn.disabled = true;
    showStatus('Generating all report cards... This may take a moment.', 'info');
    
    fetch('/api/generate-pdfs/', {
        method: 'POST',
    })
    .then(response => {
        if (response.ok) {
            const contentDisposition = response.headers.get('Content-Disposition') || '';
            let zipName = null;
            const match = contentDisposition.match(/filename\*?=([^;]+)/i);
            if (match) {
                zipName = match[1].trim().replace(/^"|"$/g, '');
                const utf8Match = zipName.match(/(?:UTF-8''|utf-8''|\")?(.+?)\"?$/i);
                if (utf8Match) zipName = utf8Match[1];
            }
            return response.blob().then(blob => {
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                if (!zipName) {
                    const term = jsSanitize((termSelect && termSelect.value) || '');
                    const year = jsSanitize((yearInput && yearInput.value) || '');
                    zipName = ['report_cards'].concat(term ? [term] : []).concat(year ? [year] : []).join('_') + '.zip';
                }
                link.download = zipName;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);

                showStatus('✓ All report cards downloaded successfully!', 'success');
                generateAllBtn.disabled = false;
            });
        } else {
            return response.json().then(data => {
                throw new Error(data.error || 'Error generating PDFs');
            });
        }
    })
    .catch(error => {
        showStatus(`Error: ${error.message}`, 'error');
        generateAllBtn.disabled = false;
    });
});

function downloadSinglePDF(e, studentIndex) {
    const event = e || window.event;
    const button = event.target.closest('.card-button');
    const originalText = button.textContent;
    button.innerHTML = '<span class="spinner"></span> Generating...';
    button.disabled = true;

    fetch('/api/generate-single/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ student_index: studentIndex }),
    })
    .then(response => {
        if (response.ok) {
            const contentDisposition = response.headers.get('Content-Disposition') || '';
            let filename = null;
            const match = contentDisposition.match(/filename\*?=([^;]+)/i);
            if (match) {
                // header may be: filename="name.pdf" or filename*=UTF-8''name.pdf
                filename = match[1].trim();
                // strip charset prefix if present
                const utf8Match = filename.match(/(?:UTF-8''|utf-8''|\")?(.+?)\"?$/i);
                if (utf8Match) filename = utf8Match[1];
                filename = filename.replace(/^"|"$/g, '');
            }
            return response.blob().then(blob => {
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                if (!filename) {
                    // fallback to student name + term + year
                    const student = allStudents[studentIndex] || {};
                    const studentName = jsSanitize(student.name || student['Student Name'] || `student_${studentIndex+1}`);
                    const term = jsSanitize((termSelect && termSelect.value) || '');
                    const year = jsSanitize((yearInput && yearInput.value) || '');
                    const parts = [studentName].concat(term ? [term] : []).concat(year ? [year] : []);
                    filename = parts.join('_') + '.pdf';
                }
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);

                button.textContent = originalText;
                button.disabled = false;
            });
        } else {
            return response.json().then(data => {
                throw new Error(data.error || 'Error generating PDF');
            });
        }
    })
    .catch(error => {
        showStatus(`Error: ${error.message}`, 'error');
        button.textContent = originalText;
        button.disabled = false;
    });
}

function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `status-message ${type}`;
    
    if (type !== 'info') {
        setTimeout(() => {
            uploadStatus.className = 'status-message';
        }, 5000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('App ready');
});
