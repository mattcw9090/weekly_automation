// Location Schedule Data
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
    },
    'Kingsway': {
        'Monday': { opening: 8.5, closing: 22 },   // 8:30 AM - 10:00 PM
        'Tuesday': { opening: 8.5, closing: 22 },  // 8:30 AM - 10:00 PM
        'Wednesday': { opening: 8.5, closing: 22 },// 8:30 AM - 10:00 PM
        'Thursday': { opening: 8.5, closing: 22 }, // 8:30 AM - 10:00 PM
        'Friday': { opening: 8.5, closing: 21 },   // 8:30 AM - 9:00 PM
        'Saturday': { opening: 9, closing: 17 },    // 9:00 AM - 5:00 PM
        'Sunday': { opening: 10, closing: 17 }      // 10:00 AM - 5:00 PM
    }
};

// Rates Data Structure
const ratesData = {
    'PBA Malaga': {
        'allCourts': {
            'weekday': [
                { start: '00:00', end: '17:00', rate: 19 },
                { start: '17:00', end: '24:00', rate: 29 }
            ],
            'weekend': [
                { start: '00:00', end: '24:00', rate: 29 }
            ]
        }
    },
    'PBA Canningvale': {
        'Hebat Court': {
            'weekday': [
                { start: '00:00', end: '17:00', rate: 16 },
                { start: '17:00', end: '24:00', rate: 26 }
            ],
            'weekend': [
                { start: '00:00', end: '24:00', rate: 26 }
            ]
        },
        'Super Court': {
            'weekday': [
                { start: '00:00', end: '17:00', rate: 19 },
                { start: '17:00', end: '24:00', rate: 29 }
            ],
            'weekend': [
                { start: '00:00', end: '24:00', rate: 29 }
            ]
        }
    }
};

// Utility Functions
const convertTimeToMinutes = timeStr => {
    const [hour, minute] = timeStr.split(':').map(Number);
    return hour * 60 + minute;
};

const validateMonday = (dateStr) => {
    const date = new Date(dateStr);
    return date.getDay() === 1; // 1 corresponds to Monday
};

const getOpeningClosingTimes = (location, day) => locationSchedule[location]?.[day] || { opening: 0, closing: 0 };

const generateTimeOptions = (location, day) => {
    const { opening, closing } = getOpeningClosingTimes(location, day);
    let options = '';
    const openingMin = Math.round(opening * 60);
    const closingMin = Math.round(closing * 60);

    for (let t = openingMin; t <= closingMin; t += 30) {
        if (t > closingMin) break;

        const h = Math.floor(t / 60);
        const m = t % 60;
        const hour12 = h % 12 || 12;
        const minuteStr = m.toString().padStart(2, '0');
        const period = h < 12 ? 'AM' : 'PM';
        const timeLabel = `${hour12}:${minuteStr} ${period}`;
        const timeValue = `${h.toString().padStart(2, '0')}:${minuteStr}`;
        options += `<option value="${timeValue}">${timeLabel}</option>`;
    }

    return options;
};

const populateDropdown = (select, options, selectedValue = '', placeholder = 'Select') => {
    const type = select.dataset.type || '';
    select.innerHTML = options
        ? `<option value="">${placeholder} ${type}</option>${options}`
        : `<option value="">Select Time</option>`;
    if (selectedValue) select.value = selectedValue;
};

const calculateCredits = (start, end, location, type, day) => {
    if (!start || !end || !location || !day) return '';
    if (location === 'PBA Canningvale' && !type) return '';
    if (location === 'Kingsway' && !type) return '';

    const startMin = convertTimeToMinutes(start);
    const endMin = convertTimeToMinutes(end);
    if (endMin <= startMin) return '';

    // Determine if the day is a weekend
    const weekendDays = ['Saturday', 'Sunday'];
    const dayType = weekendDays.includes(day) ? 'weekend' : 'weekday';

    let applicableRates = [];

    // Check if the location exists in ratesData
    if (ratesData[location]) {
        if (location === 'PBA Malaga') {
            // For PBA Malaga, use 'allCourts'
            applicableRates = ratesData[location].allCourts[dayType];
        } else if (location === 'PBA Canningvale') {
            // For PBA Canningvale, rates depend on court type
            const courtTypeKey = type || 'allCourts'; // Fallback to 'allCourts' if type is undefined
            if (ratesData[location][type]) {
                applicableRates = ratesData[location][type][dayType];
            } else {
                // If court type not found, default to 'Super Court' rates or handle accordingly
                applicableRates = ratesData[location]['Super Court'][dayType];
            }
        }
    }

    // If rates are defined in ratesData, use them
    if (applicableRates.length > 0) {
        let credits = [];
        let remainingStart = startMin;
        const sessionEnd = endMin;

        applicableRates.forEach(ratePeriod => {
            const periodStart = convertTimeToMinutes(ratePeriod.start);
            const periodEnd = convertTimeToMinutes(ratePeriod.end);
            const rate = ratePeriod.rate;

            // Find overlap between rate period and session
            const overlapStart = Math.max(remainingStart, periodStart);
            const overlapEnd = Math.min(sessionEnd, periodEnd);

            if (overlapStart < overlapEnd) {
                const duration = overlapEnd - overlapStart;
                const hours = Math.floor(duration / 60);
                const halfHours = (duration % 60) / 30;

                if (hours > 0) {
                    credits.push(`${hours}x $${rate.toFixed(2)}`);
                }
                if (halfHours > 0) {
                    credits.push(`1x $${(rate / 2).toFixed(2)}`);
                }

                remainingStart = overlapEnd;
            }
        });

        return credits.join('<br>');
    }

    // Fallback to existing logic if location not in ratesData
    // Existing logic for 'Kingsway' and other locations
    const rateChangePoints = ['PBA Malaga', 'PBA Canningvale'].includes(location) && !['Saturday', 'Sunday'].includes(day)
        ? [17 * 60, endMin].sort((a, b) => a - b)
        : [endMin];

    let credits = [], currentStart = startMin;

    rateChangePoints.forEach(nextChange => {
        const currentEnd = Math.min(nextChange, endMin);
        const isWeekendOrAfter5PM = ['Saturday', 'Sunday'].includes(day) || currentStart >= 17 * 60;
        let rate = 0;
        if (location === 'PBA Malaga') {
            rate = isWeekendOrAfter5PM ? 29 : 19;
        }
        if (location === 'PBA Canningvale') {
            rate = type === 'Hebat Court' ? (isWeekendOrAfter5PM ? 26 : 16) : (isWeekendOrAfter5PM ? 29 : 19);
        }
        if (location === 'Kingsway') {
            // Assuming 'Kingsway' rates are as per original comments
            if (!['Saturday', 'Sunday'].includes(day)) {
                rate = currentStart >= 8.5 * 60 ? 19 : 0; // 8:30 AM is 8.5*60=510 minutes
            } else {
                rate = 29; // Weekend rate
            }
        }

        const duration = currentEnd - currentStart;
        const hours = Math.floor(duration / 60);
        const halfHours = (duration % 60) / 30;
        if (hours) credits.push(`${hours}x $${rate.toFixed(2)}`);
        if (halfHours) credits.push(`1x $${(rate / 2).toFixed(2)}`);
        currentStart = currentEnd;
    });

    return credits.join('<br>');
};

// Global Data
let studentsData = [];

// Populate Student Dropdown
const populateStudentNameDropdown = select => {
    select.innerHTML = '<option value="">Select Student</option>' +
        studentsData.map(s =>
            `<option value="${s.name}" data-contact-preference="${s.contactPreference}" data-contact-info="${s.contactInfo}">
                ${s.name}
            </option>`
        ).join('');
};

// Add New Row
const addNewRow = (session = {}) => {
    const tableBody = document.querySelector('#studentTable tbody');
    const newRow = document.createElement('tr');
    newRow.innerHTML = `
        <td>
            <select name="studentName[]" class="student-name" data-type="Student" required></select>
        </td>
        <td>
            <select name="dayOfWeek[]" class="day-of-week" data-type="Day" required>
                <option value="">Select Day</option>
                ${['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
                    .map(day => `<option value="${day}">${day}</option>`).join('')}
            </select>
        </td>
        <td>
            <select name="courtLocation[]" class="court-location" data-type="Location" required>
                <option value="">Select Location</option>
                ${['PBA Canningvale','PBA Malaga','Kingsway']
                    .map(loc => `<option value="${loc}">${loc}</option>`).join('')}
            </select>
        </td>
        <td>
            <select name="courtType[]" class="court-type hidden" data-type="Type">
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

    // Populate dropdowns
    const studentSelect = newRow.querySelector('.student-name');
    populateStudentNameDropdown(studentSelect);
    studentSelect.value = session.studentName || '';

    const daySelect = newRow.querySelector('.day-of-week');
    daySelect.value = session.dayOfWeek || '';

    const locationSelect = newRow.querySelector('.court-location');
    locationSelect.value = session.courtLocation || '';

    const courtTypeSelect = newRow.querySelector('.court-type');
    courtTypeSelect.value = session.courtType || '';

    // Handle location-based UI
    const buyCreditsButton = newRow.querySelector('.buy-credits-button');
    const bookCourtButton = newRow.querySelector('.book-court-button');

    if (session.courtLocation === 'PBA Canningvale') {
        // Show court type for PBA Canningvale
        courtTypeSelect.classList.remove('hidden');
        courtTypeSelect.required = true;
        // Show both action buttons for PBA Canningvale
        buyCreditsButton.style.display = '';
        bookCourtButton.style.display = '';
    } else if (session.courtLocation === 'Kingsway') {
        // Hide court type for Kingsway
        courtTypeSelect.classList.add('hidden');
        courtTypeSelect.required = false;
        courtTypeSelect.value = '';
        // Hide Buy Credits and Book Court for Kingsway
        buyCreditsButton.style.display = 'none';
        bookCourtButton.style.display = 'none';
    } else {
        // For PBA Malaga or if location not yet selected:
        courtTypeSelect.classList.add('hidden');
        courtTypeSelect.required = false;
        courtTypeSelect.value = '';
        buyCreditsButton.style.display = '';
        bookCourtButton.style.display = '';
    }

    populateTimeDropdowns(newRow, session.sessionStart, session.sessionEnd);
    updateCredits();
};

// Populate Time Dropdowns
const populateTimeDropdowns = (row, start = '', end = '') => {
    const location = row.querySelector('.court-location').value;
    const day = row.querySelector('.day-of-week').value;

    if (!location || !day) {
        ['.session-start', '.session-end'].forEach(cls => {
            const select = row.querySelector(cls);
            select.innerHTML = '<option value="">Select Time</option>';
        });
        return;
    }

    const options = generateTimeOptions(location, day);
    ['.session-start', '.session-end'].forEach(cls => {
        const select = row.querySelector(cls);
        populateDropdown(select, options, cls === '.session-start' ? start : end, 'Select Time');
    });

    if (start) row.querySelector('.session-start').value = start;
    if (end) row.querySelector('.session-end').value = end;

    handleSessionStartChange({ target: row.querySelector('.session-start') });
};

// Update Credits for All Rows
const updateCredits = () => {
    document.querySelectorAll('#studentTable tbody tr').forEach(row => {
        const start = row.querySelector('.session-start').value;
        const end = row.querySelector('.session-end').value;
        const location = row.querySelector('.court-location').value;
        const type = row.querySelector('.court-type').value;
        const day = row.querySelector('.day-of-week').value;
        row.querySelector('.credits-to-buy').innerHTML = calculateCredits(start, end, location, type, day);
    });
};

// Event Handlers

// Handle Session Start Change
const handleSessionStartChange = event => {
    const row = event.target.closest('tr');
    const startTime = event.target.value;
    const endSelect = row.querySelector('.session-end');
    const startMinutes = convertTimeToMinutes(startTime);

    Array.from(endSelect.options).forEach(option => {
        option.disabled = convertTimeToMinutes(option.value) <= startMinutes;
    });

    if (convertTimeToMinutes(endSelect.value) <= startMinutes) endSelect.value = '';
    updateCredits();
};

// Handle Court Location Change
const handleCourtLocationChange = event => {
    const row = event.target.closest('tr');
    const courtType = row.querySelector('.court-type');
    const location = event.target.value;
    const buyCreditsBtn = row.querySelector('.buy-credits-button');
    const bookCourtBtn = row.querySelector('.book-court-button');

    if (location === 'PBA Canningvale') {
        courtType.classList.remove('hidden');
        courtType.required = true;
        if (buyCreditsBtn) buyCreditsBtn.style.display = '';
        if (bookCourtBtn) bookCourtBtn.style.display = '';
    } else if (location === 'Kingsway') {
        courtType.classList.add('hidden');
        courtType.required = false;
        courtType.value = '';
        if (buyCreditsBtn) buyCreditsBtn.style.display = 'none';
        if (bookCourtBtn) bookCourtBtn.style.display = 'none';
    } else {
        // PBA Malaga or if no location yet
        courtType.classList.add('hidden');
        courtType.required = false;
        courtType.value = '';
        if (buyCreditsBtn) buyCreditsBtn.style.display = '';
        if (bookCourtBtn) bookCourtBtn.style.display = '';
    }

    populateTimeDropdowns(row);
    updateCredits();
};

// Handle Day of Week Change
const handleDayOfWeekChange = event => {
    const row = event.target.closest('tr');
    populateTimeDropdowns(row);
    updateCredits();
};

// Handle Court Type Change
const handleCourtTypeChange = () => updateCredits();

// Delete a Row
const deleteRow = event => {
    event.target.closest('tr').remove();
    updateCredits();
};

// Handle Button Clicks
const handleButtonClick = event => {
    const row = event.target.closest('tr');
    const action = event.target.className.split(' ').find(cls =>
        ['delete-row','message-button','buy-credits-button','book-court-button','add-to-calendar-button'].includes(cls)
    );

    if (!action) return;

    switch(action) {
        case 'delete-row':
            deleteRow(event);
            break;
        case 'message-button':
            handleMessage(row);
            break;
        case 'buy-credits-button':
            handleBuyCredits(row);
            break;
        case 'book-court-button':
            handleBookCourt(row);
            break;
        case 'add-to-calendar-button':
            handleAddToCalendar(row);
            break;
    }
};

// Action Handlers

// Handle Messaging a Student
const handleMessage = row => {
    const studentName = row.querySelector('.student-name').value;
    if (!studentName) return alert('Please select a student.');

    const student = studentsData.find(s => s.name === studentName);
    if (!student) return alert('Student data not found.');

    const courtLocation = row.querySelector('.court-location').value;
    const dayOfWeek = row.querySelector('.day-of-week').value;
    const sessionStart = row.querySelector('.session-start').value;
    const sessionEnd = row.querySelector('.session-end').value;

    if (!courtLocation || !dayOfWeek || !sessionStart || !sessionEnd) {
        return alert('Please complete all session details before messaging.');
    }

    const data = {
        contactPreference: student.contactPreference,
        contactInfo: student.contactInfo,
        studentName,
        courtLocation,
        dayOfWeek,
        startTime: sessionStart,
        endTime: sessionEnd,
    };

    fetch('/message-student', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    .then(response => response.text())
    .then(result => alert(result))
    .catch(() => alert('An error occurred while messaging the student.'));
};

// Handle Buying Credits
const handleBuyCredits = row => {
    const credits = row.querySelector('.credits-to-buy').innerHTML;
    if (!credits) return alert('No credits to buy.');

    fetch('/buy-credits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creditsToBuy: credits }),
    })
    .then(response => response.text())
    .then(result => alert(result))
    .catch(() => alert('An error occurred while buying credits.'));
};

// Handle Booking a Court
const handleBookCourt = row => {
    const startingWeek = document.getElementById('weekStarting').value;
    const data = {
        startingWeek,
        dayOfWeek: row.querySelector('.day-of-week').value,
        courtLocation: row.querySelector('.court-location').value,
        courtType: row.querySelector('.court-type').value,
        sessionStart: row.querySelector('.session-start').value,
        sessionEnd: row.querySelector('.session-end').value
    };

    fetch('/book-court', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    .then(response => response.text())
    .then(result => alert(result))
    .catch(() => alert('An error occurred while booking court.'));
};

// Handle Adding to Calendar
const handleAddToCalendar = row => {
    const startingWeek = document.getElementById('weekStarting').value;
    const data = {
        startingWeek,
        studentName: row.querySelector('.student-name').value,
        dayOfWeek: row.querySelector('.day-of-week').value,
        courtLocation: row.querySelector('.court-location').value,
        sessionStart: row.querySelector('.session-start').value,
        sessionEnd: row.querySelector('.session-end').value
    };

    fetch('/add-to-calendar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    .then(response => response.text())
    .then(result => alert(result))
    .catch(() => alert('An error occurred while adding to calendar.'));
};

// Initialize Event Listeners
const initializeEventListeners = () => {
    const tableBody = document.querySelector('#studentTable tbody');

    // Change Events
    tableBody.addEventListener('change', event => {
        const target = event.target;
        if (target.classList.contains('court-location')) handleCourtLocationChange(event);
        if (target.classList.contains('day-of-week')) handleDayOfWeekChange(event);
        if (target.classList.contains('session-start')) handleSessionStartChange(event);
        if (target.classList.contains('session-end')) updateCredits();
        if (target.classList.contains('court-type')) handleCourtTypeChange(event);
    });

    // Click Events
    tableBody.addEventListener('click', handleButtonClick);

    // Add Row Button
    document.getElementById('addRow').addEventListener('click', () => addNewRow());

    // Save Config Button
    document.getElementById('saveConfigButton').addEventListener('click', async () => {
        const configData = {
            weekStarting: document.getElementById('weekStarting').value,
            sessions: Array.from(document.querySelectorAll('#studentTable tbody tr')).map(row => ({
                studentName: row.querySelector('.student-name').value,
                dayOfWeek: row.querySelector('.day-of-week').value,
                courtLocation: row.querySelector('.court-location').value,
                sessionStart: row.querySelector('.session-start').value,
                sessionEnd: row.querySelector('.session-end').value,
                courtType: row.querySelector('.court-type').value,
                statusMessaged: row.querySelector('input[name="statusMessaged[]"]').checked,
                statusBooked: row.querySelector('input[name="statusBooked[]"]').checked
            }))
        };

        try {
            const response = await fetch('/save-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });
            const result = await response.json();
            alert(response.ok ? result.message : `Failed to save: ${result.error}`);
        } catch {
            alert('An error occurred while saving configuration.');
        }
    });

    // Week Starting date validation
    const weekStartingInput = document.getElementById('weekStarting');
    weekStartingInput.addEventListener('change', function () {
        if (this.value && !validateMonday(this.value)) {
            alert('Please select a Monday for "Week Starting".');
            this.value = '';
        }
    });
};

// Load Configuration Data
const loadConfig = data => {
    document.getElementById('weekStarting').value = data.weekStarting || '';
    document.querySelector('#studentTable tbody').innerHTML = '';
    data.sessions.forEach(session => addNewRow(session));
};

// Fetch Initial Data
document.addEventListener('DOMContentLoaded', () => {
    Promise.all([fetch('/students'), fetch('/config')])
        .then(async ([studentsRes, configRes]) => {
            if (!studentsRes.ok || !configRes.ok) throw new Error('Failed to fetch data');
            studentsData = await studentsRes.json();
            const configData = await configRes.json();
            if (configData.error) throw new Error(configData.error);
            loadConfig(configData);
        })
        .catch(error => {
            console.error(error);
            addNewRow(); // Add a default row if fetching fails
        })
        .finally(initializeEventListeners);
});
