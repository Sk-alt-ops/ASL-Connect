/* ===== ASL Connect — Landing Page Scripts ===== */

/* ===== PAGE NAVIGATION ===== */
function navigateToPage(pageId) {
    const pages = document.querySelectorAll('.page');
    const target = document.getElementById('page-' + pageId);
    if (!target || target.classList.contains('active')) return;

    pages.forEach(p => p.classList.remove('active'));
    target.classList.add('active');

    const navLinks = document.querySelectorAll('.nav-links a, .footer-col a[href^="#"]');
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === '#' + pageId) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    if (menuOpen) closeMobileMenu();
}

document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        e.preventDefault();
        navigateToPage(href.replace('#', ''));
    });
});

document.querySelectorAll('.mobile-menu ul li a').forEach(link => {
    link.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        e.preventDefault();
        navigateToPage(href.replace('#', ''));
    });
});

document.querySelectorAll('.footer-col a[href^="#"]').forEach(link => {
    link.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        const pageId = href.replace('#', '');
        if (document.getElementById('page-' + pageId)) {
            e.preventDefault();
            navigateToPage(pageId);
        }
    });
});

document.querySelectorAll('.hero-buttons a[href^="#"], .testimonials-cta a[href^="#"]').forEach(link => {
    link.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        const pageId = href.replace('#', '');
        if (document.getElementById('page-' + pageId)) {
            e.preventDefault();
            navigateToPage(pageId);
        }
    });
});

/* ===== HERO ANIMATION ===== */
const heroTitle = document.querySelector('.hero-title');
const heroSubtitle = document.querySelector('.hero-subtitle');
const heroButtons = document.querySelector('.hero-buttons');
const heroStats = document.querySelector('.hero-stats');

function triggerHeroAnimation() {
    if (heroTitle) heroTitle.style.animationPlayState = 'running';
}
window.addEventListener('load', triggerHeroAnimation);

/* ===== HAMBURGER MENU ===== */
const hamburgerBtn = document.getElementById('hamburgerBtn');
const mobileMenu = document.getElementById('mobileMenu');
let menuOpen = false;

function openMobileMenu() {
    menuOpen = true;
    hamburgerBtn.classList.add('open');
    hamburgerBtn.setAttribute('aria-expanded', 'true');
    mobileMenu.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeMobileMenu() {
    menuOpen = false;
    hamburgerBtn.classList.remove('open');
    hamburgerBtn.setAttribute('aria-expanded', 'false');
    mobileMenu.classList.remove('open');
    document.body.style.overflow = '';
}

hamburgerBtn.addEventListener('click', () => {
    if (menuOpen) {
        closeMobileMenu();
    } else {
        openMobileMenu();
    }
});

document.addEventListener('click', (e) => {
    if (menuOpen && !mobileMenu.contains(e.target) && !hamburgerBtn.contains(e.target)) {
        closeMobileMenu();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && menuOpen) {
        closeMobileMenu();
    }
});

window.addEventListener('resize', () => {
    if (window.innerWidth > 768 && menuOpen) {
        closeMobileMenu();
    }
});

/* ===== CONTACT FORM ===== */
function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith('csrftoken=')) {
            return cookie.substring('csrftoken='.length);
        }
    }
    return '';
}

function submitContactForm(form) {
    const formData = new FormData(form);
    const data = {
        name: formData.get('name') || '',
        email: formData.get('email') || '',
        subject: formData.get('subject') || '',
        message: formData.get('message') || '',
    };

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Sending...';

    const existingAlert = form.querySelector('.contact-alert');
    if (existingAlert) existingAlert.remove();

    fetch(form.action, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify(data),
    })
    .then(r => r.json())
    .then(result => {
        const alert = document.createElement('div');
        alert.className = 'contact-alert';

        if (result.success) {
            alert.className += ' success';
            alert.textContent = result.message || 'Your message has been sent successfully. We will contact you via email soon.';
            form.reset();
        } else {
            alert.className += ' error';
            if (result.errors) {
                const errorList = Object.values(result.errors).join('. ');
                alert.textContent = errorList;
            } else {
                alert.textContent = result.error || 'An error occurred. Please try again.';
            }
        }

        form.insertBefore(alert, form.firstChild);
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;

        setTimeout(() => { alert.remove(); }, result.success ? 8000 : 5000);
    })
    .catch(() => {
        const alert = document.createElement('div');
        alert.className = 'contact-alert error';
        alert.textContent = 'Network error. Please try again.';
        form.insertBefore(alert, form.firstChild);
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    });
}
