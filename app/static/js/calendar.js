// static/js/calendar.js
(() => {
  'use strict';

  window.addEventListener('DOMContentLoaded', () => {
    const dataDiv = document.querySelector('[data-calendar-events]');
    const EVENTS_URL = dataDiv.dataset.calendarEvents;
    const MONTH_URL = dataDiv.dataset.calendarMonth;

    const $ = s => document.querySelector(s);
    const prevMonthBtn = $('#prevMonth');
    const nextMonthBtn = $('#nextMonth');
    const currentMonthTitle = $('#currentMonth');
    const calendarGrid = $('#calendarGrid');
    const eventModal = $('#eventModal');
    const eventTitle = $('#eventTitle');
    const eventDetails = $('#eventDetails');
    const eventLink = $('#eventLink');
    const closeModal = $('#closeModal');

    let currentDate = new Date();
    let events = [];

    function urlReplace(base, year, month) {
      return base.replace(/\/0\/0($|\/)/, `/${year}/${month}$1`);
    }

    async function fetchJSON(url, opt) {
      const r = await fetch(url, opt);
      let data = null; 
      try { data = await r.json(); } catch {}
      if (!r.ok) throw new Error((data && (data.message || data.error)) || `${r.status} ${r.statusText}`);
      return data;
    }

    function formatDate(dateStr) {
      if (!dateStr) return '';
      const date = new Date(dateStr + 'T00:00:00');
      return date.toLocaleDateString('lt-LT');
    }

    function parseDate(dateStr) {
      if (!dateStr) return null;
      return new Date(dateStr + 'T00:00:00');
    }

    function isSameDay(date1, date2) {
      return date1.getDate() === date2.getDate() &&
             date1.getMonth() === date2.getMonth() &&
             date1.getFullYear() === date2.getFullYear();
    }

    function isDateInRange(date, startStr, endStr) {
      const start = parseDate(startStr);
      const end = parseDate(endStr);
      
      if (!start && !end) return false;
      if (!start) return date <= end;
      if (!end) return date >= start;
      return date >= start && date <= end;
    }

    async function loadEvents() {
      try {
        events = await fetchJSON(`${EVENTS_URL}?year=${currentDate.getFullYear()}&month=${currentDate.getMonth() + 1}`);
      } catch (e) {
        console.error('Error loading events:', e);
        events = [];
      }
    }

    async function loadMonth() {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1;
      
      try {
        const monthData = await fetchJSON(urlReplace(MONTH_URL, year, month));
        currentMonthTitle.textContent = `${monthData.month_name} ${year}`;
        renderCalendar(monthData);
      } catch (e) {
        console.error('Error loading month:', e);
      }
    }

    function renderCalendar(monthData) {
      calendarGrid.innerHTML = '';
      
      monthData.calendar.forEach(week => {
        week.forEach(day => {
          const dayElement = document.createElement('div');
          dayElement.className = 'min-h-32 border-r border-b border-slate-200 p-2 relative';
          
          if (day === 0) {
            // Empty day from previous/next month
            dayElement.classList.add('bg-slate-50');
          } else {
            const currentDayDate = new Date(monthData.year, monthData.month - 1, day);
            const today = new Date();
            
            // Day number
            const dayNumber = document.createElement('div');
            dayNumber.className = 'font-medium text-slate-900 mb-1';
            if (isSameDay(currentDayDate, today)) {
              dayNumber.classList.add('bg-brand-100', 'text-brand-800', 'rounded-full', 'w-6', 'h-6', 'flex', 'items-center', 'justify-center', 'text-xs');
            }
            dayNumber.textContent = day;
            dayElement.appendChild(dayNumber);
            
            // Events for this day
            const dayEvents = events.filter(event => {
              return isDateInRange(currentDayDate, event.start, event.end);
            });
            
            dayEvents.forEach(event => {
              const eventElement = document.createElement('div');
              eventElement.className = `text-xs p-1 mb-1 rounded cursor-pointer truncate transition-colors ${
                event.type === 'campaign' ? 'bg-brand-100 text-brand-800 hover:bg-brand-200' : 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
              }`;
              eventElement.textContent = event.title;
              eventElement.addEventListener('click', () => showEventDetails(event));
              dayElement.appendChild(eventElement);
            });
          }
          
          calendarGrid.appendChild(dayElement);
        });
      });
    }

    function showEventDetails(event) {
      eventTitle.textContent = event.title;
      eventLink.href = event.url || '#';
      
      const details = [];
      if (event.campaign_name && event.type === 'wave') {
        details.push(`<strong>Kampanija:</strong> ${event.campaign_name}`);
      }
      if (event.start || event.end) {
        const startDate = event.start ? formatDate(event.start) : '?';
        const endDate = event.end ? formatDate(event.end) : '?';
        details.push(`<strong>Laikotarpis:</strong> ${startDate} - ${endDate}`);
      }
      if (event.status) {
        const statusLabels = {
          'draft': 'Juodraštis',
          'confirmed': 'Patvirtinta',
          'orders_sent': 'Užsakymai išsiųsti',
          'active': 'Aktyvi',
          'completed': 'Užbaigta'
        };
        details.push(`<strong>Statusas:</strong> ${statusLabels[event.status] || event.status}`);
      }
      
      eventDetails.innerHTML = details.join('<br>');
      eventModal.classList.remove('hidden');
    }

    function hideEventDetails() {
      eventModal.classList.add('hidden');
    }

    async function navigateMonth(direction) {
      currentDate.setMonth(currentDate.getMonth() + direction);
      await loadEvents();
      await loadMonth();
    }

    // Event listeners
    prevMonthBtn.addEventListener('click', () => navigateMonth(-1));
    nextMonthBtn.addEventListener('click', () => navigateMonth(1));
    closeModal.addEventListener('click', hideEventDetails);
    eventModal.addEventListener('click', (e) => {
      if (e.target === eventModal) hideEventDetails();
    });

    // Initial load
    (async () => {
      await loadEvents();
      await loadMonth();
    })();
  });
})();