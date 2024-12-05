// Utility function to convert time string to minutes
function convertTimeToMinutes(timeStr) {
    const [hourStr, minuteStr] = timeStr.split(':');
    return parseInt(hourStr, 10) * 60 + parseInt(minuteStr, 10);
}

// Data for opening and closing times based on location and day
const locationSchedule = {
    'PBA Malaga': {
        'Monday': { opening: 13, closing: 22 },
        'Tuesday': { opening: 13, closing: 22 },
        'Wednesday': { opening: 13, closing: 22 },
        'Thursday': { opening: 9, closing: 22 },
        'Friday': { opening: 9, closing: 22 },
        'Saturday': { opening: 9, closing: 22 },
        'Sunday': { opening: 9, closing: 22 }
    },
    'PBA Canningvale': {
        'Monday': { opening: 10, closing: 22 },
        'Tuesday': { opening: 10, closing: 22 },
        'Wednesday': { opening: 10, closing: 22 },
        'Thursday': { opening: 10, closing: 22 },
        'Friday': { opening: 10, closing: 22 },
        'Saturday': { opening: 9, closing: 22 },
        'Sunday': { opening: 9, closing: 20 }
    }
};

// Function to get opening and closing times
function getOpeningClosingTimes(location, day) {
    return locationSchedule[location]?.[day] || { opening: 0, closing: 0 };
}

// Function to generate time options
function generateTimeOptions(location, day) {
    const { opening, closing } = getOpeningClosingTimes(location, day);
    let options = '';

    for (let h = opening; h <= closing; h++) {
        for (let m = 0; m < 60; m += 30) {
            if (h === closing && m > 0) break;
            const hour12 = h % 12 || 12;
            const minute = m.toString().padStart(2, '0');
            const period = h < 12 ? 'AM' : 'PM';
            const timeLabel = `${hour12}:${minute} ${period}`;
            const timeValue = `${h.toString().padStart(2, '0')}:${minute}`;
            options += `<option value="${timeValue}">${timeLabel}</option>`;
        }
    }
    return options;
}

// Function to populate time dropdowns
function populateTimeDropdowns(row, selectedStartTime = '', selectedEndTime = '') {
    const location = row.querySelector('.court-location').value;
    const day = row.querySelector('.day-of-week').value;
    const sessionStartSelect = row.querySelector('.session-start');
    const sessionEndSelect = row.querySelector('.session-end');

    if (!location || !day) {
        sessionStartSelect.innerHTML = '<option value="">Select Time</option>';
        sessionEndSelect.innerHTML = '<option value="">Select Time</option>';
        return;
    }

    const timeOptions = generateTimeOptions(location, day);
    sessionStartSelect.innerHTML = '<option value="">Select Time</option>' + timeOptions;
    sessionEndSelect.innerHTML = '<option value="">Select Time</option>' + timeOptions;

    if (selectedStartTime) sessionStartSelect.value = selectedStartTime;
    if (selectedEndTime) sessionEndSelect.value = selectedEndTime;

    handleSessionStartChange({ target: sessionStartSelect });
}

// Handle session start change
function handleSessionStartChange(event) {
    const row = event.target.closest('tr');
    const sessionStartSelect = row.querySelector('.session-start');
    const sessionEndSelect = row.querySelector('.session-end');
    const selectedStartTime = sessionStartSelect.value;

    if (!selectedStartTime) {
        Array.from(sessionEndSelect.options).forEach(option => option.disabled = false);
        return;
    }

    const startTimeMinutes = convertTimeToMinutes(selectedStartTime);

    Array.from(sessionEndSelect.options).forEach(option => {
        const optionTimeMinutes = convertTimeToMinutes(option.value);
        option.disabled = optionTimeMinutes <= startTimeMinutes;
    });

    if (sessionEndSelect.value && convertTimeToMinutes(sessionEndSelect.value) <= startTimeMinutes) {
        sessionEndSelect.value = '';
    }

    updateCredits();
}

// Calculate credits based on session details
function calculateCredits(start, end, location, type, day) {
    if (!start || !end || !location || !day) return '';
    if (location === 'PBA Canningvale' && !type) return '';

    const startTotalMinutes = convertTimeToMinutes(start);
    const endTotalMinutes = convertTimeToMinutes(end);

    if (endTotalMinutes <= startTotalMinutes) return '';

    let credits = [];
    const rateChangePoints = [];

    if (location === 'PBA Malaga' || location === 'PBA Canningvale') {
        if (!['Saturday', 'Sunday'].includes(day)) {
            rateChangePoints.push(17 * 60); // 5 PM
        }
    }

    rateChangePoints.push(endTotalMinutes);
    rateChangePoints.sort((a, b) => a - b);

    let currentStart = startTotalMinutes;

    while (currentStart < endTotalMinutes) {
        const nextChange = rateChangePoints.find(point => point > currentStart) || endTotalMinutes;
        const currentEnd = Math.min(nextChange, endTotalMinutes);
        const isWeekendOrAfter5PM = ['Saturday', 'Sunday'].includes(day) || currentStart >= 17 * 60;

        let ratePerHour = 0;
        if (location === 'PBA Malaga') {
            ratePerHour = isWeekendOrAfter5PM ? 29 : 19;
        } else if (location === 'PBA Canningvale') {
            ratePerHour = (type === 'Hebat Court') ? (isWeekendOrAfter5PM ? 26 : 16) : (isWeekendOrAfter5PM ? 29 : 19);
        }

        const durationMinutes = currentEnd - currentStart;
        const fullHours = Math.floor(durationMinutes / 60);
        const halfHours = (durationMinutes % 60) / 30;

        if (fullHours > 0) credits.push(`${fullHours}x $${ratePerHour.toFixed(2)}`);
        if (halfHours > 0) credits.push(`1x $${(ratePerHour / 2).toFixed(2)}`);

        currentStart = currentEnd;
    }

    return credits.join('<br>');
}

// Update credits for all rows
function updateCredits() {
    document.querySelectorAll('#studentTable tbody tr').forEach(row => {
        const start = row.querySelector('.session-start').value;
        const end = row.querySelector('.session-end').value;
        const location = row.querySelector('.court-location').value;
        const type = row.querySelector('.court-type').value;
        const day = row.querySelector('.day-of-week').value;
        const creditsCell = row.querySelector('.credits-to-buy');
        creditsCell.innerHTML = calculateCredits(start, end, location, type, day);
    });
}

// Delete a row
function deleteRow(event) {
    event.target.closest('tr').remove();
    updateCredits();
}

// Handle court location change
function handleCourtLocationChange(event) {
    const row = event.target.closest('tr');
    const courtTypeSelect = row.querySelector('.court-type');
    const location = event.target.value;

    if (location === 'PBA Canningvale') {
        courtTypeSelect.classList.remove('hidden');
        courtTypeSelect.setAttribute('required', 'required');
    } else {
        courtTypeSelect.classList.add('hidden');
        courtTypeSelect.removeAttribute('required');
        courtTypeSelect.value = '';
    }

    populateTimeDropdowns(row);
    updateCredits();
}

// Handle day of week change
function handleDayOfWeekChange(event) {
    const row = event.target.closest('tr');
    populateTimeDropdowns(row);
    updateCredits();
}

// Handle court type change
function handleCourtTypeChange() {
    updateCredits();
}

// Update event listeners using event delegation
function updateEventListeners() {
    const tableBody = document.querySelector('#studentTable tbody');

    tableBody.removeEventListener('click', actionsHandler);
    tableBody.addEventListener('click', actionsHandler);

    tableBody.removeEventListener('change', tableBodyChangeHandler);
    tableBody.addEventListener('change', tableBodyChangeHandler);
}

// Event delegation for change events in the table body
function tableBodyChangeHandler(event) {
    if (event.target.classList.contains('court-location')) {
        handleCourtLocationChange(event);
    } else if (event.target.classList.contains('day-of-week')) {
        handleDayOfWeekChange(event);
    } else if (event.target.classList.contains('session-start')) {
        handleSessionStartChange(event);
    } else if (event.target.classList.contains('session-end')) {
        updateCredits();
    } else if (event.target.classList.contains('court-type')) {
        handleCourtTypeChange();
    }
}

// Fetch students data and store globally
window.studentsData = [];

document.addEventListener('DOMContentLoaded', () => {
    // Fetch students data
    fetch('/students')
        .then(response => response.json())
        .then(studentsData => {
            // Store studentsData globally
            window.studentsData = studentsData;

            // Now initialize the form
            document.getElementById('addRow').click();
            updateEventListeners();
        })
        .catch(error => {
            console.error('Error fetching students data:', error);
        });
});

// Function to populate student name dropdown
function populateStudentNameDropdown(selectElement) {
    const studentsData = window.studentsData || [];
    selectElement.innerHTML = '<option value="">Select Student</option>';
    studentsData.forEach(student => {
        const option = document.createElement('option');
        option.value = student.name;
        option.textContent = student.name;
        option.dataset.contactPreference = student.contactPreference;
        option.dataset.contactInfo = student.contactInfo;
        selectElement.appendChild(option);
    });
}

// Modify addRow to include student name dropdown
document.getElementById('addRow').addEventListener('click', () => {
    const tableBody = document.querySelector('#studentTable tbody');
    const newRow = document.createElement('tr');
    newRow.innerHTML = `
        <td>
            <select name="studentName[]" class="student-name" required>
                <!-- options will be populated via JavaScript -->
            </select>
        </td>
        <td>
            <select name="dayOfWeek[]" class="day-of-week" required>
                <option value="">Select Day</option>
                <option value="Monday">Monday</option>
                <option value="Tuesday">Tuesday</option>
                <option value="Wednesday">Wednesday</option>
                <option value="Thursday">Thursday</option>
                <option value="Friday">Friday</option>
                <option value="Saturday">Saturday</option>
                <option value="Sunday">Sunday</option>
            </select>
        </td>
        <td>
            <select name="courtLocation[]" class="court-location" required>
                <option value="">Select Location</option>
                <option value="PBA Canningvale">PBA Canningvale</option>
                <option value="PBA Malaga">PBA Malaga</option>
            </select>
        </td>
        <td>
            <select name="courtType[]" class="court-type hidden">
                <option value="">Select Type</option>
                <option value="Hebat Court">Hebat Court</option>
                <option value="Super Court">Super Court</option>
            </select>
        </td>
        <td>
            <select name="sessionStart[]" class="session-start" required>
                <option value="">Select Time</option>
            </select>
        </td>
        <td>
            <select name="sessionEnd[]" class="session-end" required>
                <option value="">Select Time</option>
            </select>
        </td>
        <td class="credits-to-buy"></td>
        <td class="status-column">
            <label><input type="checkbox" name="statusMessaged[]"> Messaged</label><br>
            <label><input type="checkbox" name="statusBooked[]"> Booked</label>
        </td>
        <td>
            <button type="button" class="message-button">Message</button>
            <button type="button" class="buy-credits-button">Buy Credits</button>
            <button type="button" class="book-court-button">Book Court</button>
            <button type="button" class="add-to-calendar-button">Add to Calendar</button>
            <button type="button" class="delete-row">Delete</button>
        </td>
    `;
    tableBody.appendChild(newRow);

    // Now populate the student name dropdown
    const studentNameSelect = newRow.querySelector('.student-name');
    populateStudentNameDropdown(studentNameSelect);

    // Existing code...
    populateTimeDropdowns(newRow);
    updateCredits();
});

// Handle "Load Config" button click
document.getElementById('loadConfigButton').addEventListener('click', () => {
    document.getElementById('configFileInput').click();
});

// Handle file input change
document.getElementById('configFileInput').addEventListener('change', handleFileSelect);

// Read and process the selected configuration file
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const configData = JSON.parse(e.target.result);
            loadConfigFile(configData);
        } catch (error) {
            alert('Invalid configuration file. Please ensure it is a valid JSON file.');
            console.error(error);
        }
    };
    reader.readAsText(file);
}

// Event delegation for click events in the table body
function actionsHandler(event) {
    if (event.target.classList.contains('delete-row')) {
        deleteRow(event);
    } else if (event.target.classList.contains('message-button')) {
        const row = event.target.closest('tr');
        const studentNameSelect = row.querySelector('.student-name');
        const studentName = studentNameSelect.value;
        if (!studentName) {
            alert('Please select a student.');
            return;
        }

        // Find the student in window.studentsData
        const student = window.studentsData.find(s => s.name === studentName);
        if (student) {
            // Retrieve additional data from the row
            const courtLocation = row.querySelector('.court-location').value;
            const dayOfWeek = row.querySelector('.day-of-week').value;
            const sessionStart = row.querySelector('.session-start').value;
            const sessionEnd = row.querySelector('.session-end').value;

            // Ensure all required fields are filled
            if (!courtLocation || !dayOfWeek || !sessionStart || !sessionEnd) {
                alert('Please complete all session details before messaging.');
                return;
            }

            // Prepare the data to send to the server
            const data = {
                contactPreference: student.contactPreference,
                contactInfo: student.contactInfo,
                studentName: studentName,
                courtLocation: courtLocation,
                dayOfWeek: dayOfWeek,
                startTime: sessionStart,
                endTime: sessionEnd,
            };

            // Send the data to the server via POST request
            fetch('/message-student', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })
                .then(response => response.text())
                .then(result => {
                    alert(result);
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while messaging the student.');
                });
        } else {
            alert('Student data not found.');
        }
    } else if (event.target.classList.contains('buy-credits-button')) {
        const row = event.target.closest('tr');
        const creditsCell = row.querySelector('.credits-to-buy');
        const creditsToBuy = creditsCell.innerHTML;

        // Prepare the data to send to the server
        const data = {
            creditsToBuy
        };

        // Send the data to the server via POST request
        fetch('/buy-credits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.text())
        .then(result => {
            alert(result);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while buying credits.');
        });
    } else if (event.target.classList.contains('book-court-button')) {
        const startingWeek = document.getElementById('weekStarting').value;
        const row = event.target.closest('tr');

        // Retrieve data from row
        const dayOfWeek = row.querySelector('.day-of-week').value;
        const courtLocation = row.querySelector('.court-location').value;
        const courtType = row.querySelector('.court-type').value;
        const sessionStart = row.querySelector('.session-start').value;
        const sessionEnd = row.querySelector('.session-end').value;

        // Prepare the data to send to the server
        const data = {
            startingWeek,
            dayOfWeek,
            courtLocation,
            courtType,
            sessionStart,
            sessionEnd
        };

        // Send the data to the server via POST request
        fetch('/book-court', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.text())
        .then(result => {
            alert(result);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while booking court.');
        });
    } else if (event.target.classList.contains('add-to-calendar-button')) {
        const startingWeek = document.getElementById('weekStarting').value;
        const row = event.target.closest('tr');

        // Retrieve data from row
        const dayOfWeek = row.querySelector('.day-of-week').value;
        const courtLocation = row.querySelector('.court-location').value;
        const sessionStart = row.querySelector('.session-start').value;
        const sessionEnd = row.querySelector('.session-end').value;

        // Prepare the data to send to the server
        const data = {
            startingWeek,
            dayOfWeek,
            courtLocation,
            sessionStart,
            sessionEnd
        };

        // Send the data to the server via POST request
        fetch('/add-to-calendar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.text())
        .then(result => {
            alert(result);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while adding to calendar.');
        });
    }
}

// Prefill the form with data from the configuration file
function loadConfigFile(data) {
    // Set the week starting date
    document.getElementById('weekStarting').value = data.weekStarting || '';

    // Clear existing rows
    const tableBody = document.querySelector('#studentTable tbody');
    tableBody.innerHTML = '';

    data.sessions.forEach(session => {
        const newRow = document.createElement('tr');
        newRow.innerHTML = `
            <td>
                <select name="studentName[]" class="student-name" required>
                    <!-- options will be populated via JavaScript -->
                </select>
            </td>
            <td>
                <select name="dayOfWeek[]" class="day-of-week" required>
                    <option value="">Select Day</option>
                    <option value="Monday">Monday</option>
                    <option value="Tuesday">Tuesday</option>
                    <option value="Wednesday">Wednesday</option>
                    <option value="Thursday">Thursday</option>
                    <option value="Friday">Friday</option>
                    <option value="Saturday">Saturday</option>
                    <option value="Sunday">Sunday</option>
                </select>
            </td>
            <td>
                <select name="courtLocation[]" class="court-location" required>
                    <option value="">Select Location</option>
                    <option value="PBA Canningvale">PBA Canningvale</option>
                    <option value="PBA Malaga">PBA Malaga</option>
                </select>
            </td>
            <td>
                <select name="courtType[]" class="court-type ${session.courtLocation === 'PBA Canningvale' ? '' : 'hidden'}">
                    <option value="">Select Type</option>
                    <option value="Hebat Court">Hebat Court</option>
                    <option value="Super Court">Super Court</option>
                </select>
            </td>
            <td>
                <select name="sessionStart[]" class="session-start" required>
                    <option value="">Select Time</option>
                </select>
            </td>
            <td>
                <select name="sessionEnd[]" class="session-end" required>
                    <option value="">Select Time</option>
                </select>
            </td>
            <td class="credits-to-buy"></td>
            <td class="status-column">
                <label><input type="checkbox" name="statusMessaged[]" ${session.statusMessaged ? 'checked' : ''}> Messaged</label><br>
                <label><input type="checkbox" name="statusBooked[]" ${session.statusBooked ? 'checked' : ''}> Booked</label>
            </td>
            <td>
                <button type="button" class="message-button">Message</button>
                <button type="button" class="buy-credits-button">Buy Credits</button>
                <button type="button" class="book-court-button">Book Court</button>
                <button type="button" class="add-to-calendar-button">Add to Calendar</button>
                <button type="button" class="delete-row">Delete</button>
            </td>
        `;
        tableBody.appendChild(newRow);

        const lastRow = tableBody.lastElementChild;

        // Populate the student name dropdown and set selected value
        const studentNameSelect = lastRow.querySelector('.student-name');
        populateStudentNameDropdown(studentNameSelect);
        studentNameSelect.value = session.studentName || '';

        // Set the values
        lastRow.querySelector('.day-of-week').value = session.dayOfWeek || '';
        lastRow.querySelector('.court-location').value = session.courtLocation || '';
        lastRow.querySelector('.court-type').value = session.courtType || '';

        // Handle court type visibility
        const courtTypeSelect = lastRow.querySelector('.court-type');
        if (session.courtLocation === 'PBA Canningvale') {
            courtTypeSelect.classList.remove('hidden');
            courtTypeSelect.setAttribute('required', 'required');
        } else {
            courtTypeSelect.classList.add('hidden');
            courtTypeSelect.removeAttribute('required');
            courtTypeSelect.value = '';
        }

        // Populate time dropdowns with selected times
        populateTimeDropdowns(lastRow, session.sessionStart || '', session.sessionEnd || '');

        // Set status checkboxes
        lastRow.querySelector('input[name="statusMessaged[]"]').checked = session.statusMessaged || false;
        lastRow.querySelector('input[name="statusBooked[]"]').checked = session.statusBooked || false;
    });

    updateEventListeners();
    updateCredits();
}

// Handle "Save Config" button click
document.getElementById('saveConfigButton').addEventListener('click', async () => {
    const configData = {
        weekStarting: document.getElementById('weekStarting').value,
        sessions: []
    };

    document.querySelectorAll('#studentTable tbody tr').forEach(row => {
        const studentName = row.querySelector('.student-name').value;
        const dayOfWeek = row.querySelector('.day-of-week').value;
        const courtLocation = row.querySelector('.court-location').value;
        const sessionStart = row.querySelector('.session-start').value;
        const sessionEnd = row.querySelector('.session-end').value;
        const courtType = row.querySelector('.court-type').value;
        const statusMessaged = row.querySelector('input[name="statusMessaged[]"]').checked;
        const statusBooked = row.querySelector('input[name="statusBooked[]"]').checked;

        const sessionData = {
            studentName,
            dayOfWeek,
            courtLocation,
            sessionStart,
            sessionEnd,
            courtType,
            statusMessaged,
            statusBooked
        };
        configData.sessions.push(sessionData);
    });

    const dataStr = JSON.stringify(configData, null, 4);

    if ('showSaveFilePicker' in window) {
        // Use the File System Access API
        try {
            const options = {
                suggestedName: 'config.json',
                types: [
                    {
                        description: 'JSON Files',
                        accept: { 'application/json': ['.json'] },
                    },
                ],
            };
            const handle = await window.showSaveFilePicker(options);
            const writableStream = await handle.createWritable();
            await writableStream.write(dataStr);
            await writableStream.close();
            alert('File saved successfully.');
        } catch (err) {
            console.error('File save failed:', err);
            alert('File save was cancelled or failed.');
        }
    } else {
        // Fallback for browsers that do not support showSaveFilePicker
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const downloadLink = document.createElement('a');
        downloadLink.href = url;
        downloadLink.download = 'config.json';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        URL.revokeObjectURL(url);
    }
});
