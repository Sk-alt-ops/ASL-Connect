/* ===== ASL Connect — Auth Modal Scripts ===== */

/*
 * Handles the login/register modal lifecycle: opening, closing,
 * tab switching, disability status toggle, and form submission.
 */

/* ===== STATE ===== */

const modal = document.getElementById('authModal');
let disabilityStatus = false;

/* ===== MODAL OPEN / CLOSE ===== */

function openModal(tab) {
    /* Close mobile menu if open before showing auth modal */
    const hamburgerBtn = document.getElementById('hamburgerBtn');
    const mobileMenu = document.getElementById('mobileMenu');
    if (hamburgerBtn && mobileMenu) {
        const isMenuOpen = hamburgerBtn.classList.contains('open');
        if (isMenuOpen) {
            hamburgerBtn.classList.remove('open');
            hamburgerBtn.setAttribute('aria-expanded', 'false');
            mobileMenu.classList.remove('open');
            document.body.style.overflow = '';
        }
    }
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    switchTab(tab);
}

function closeModal() {
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

/* ===== TAB SWITCHING ===== */

function switchTab(tab) {
    document.querySelectorAll('.modal-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    document.getElementById('registerPanel').classList.toggle('active', tab === 'register');
    document.getElementById('loginPanel').classList.toggle('active', tab === 'login');
}

/* ===== DISABILITY STATUS TOGGLE ===== */

function setDisability(val) {
    disabilityStatus = val;
    document.getElementById('btnYes').classList.toggle('active', val);
    document.getElementById('btnNo').classList.toggle('active', !val);
}

/* ===== REAL-TIME VALIDATION ===== */

document.addEventListener('DOMContentLoaded', function() {
    const emailInput = document.getElementById('regEmail');
    const passwordInput = document.getElementById('regPassword');
    const confirmInput = document.getElementById('regConfirm');

    if (emailInput) {
        emailInput.addEventListener('input', function() {
            const wrap = this.closest('.modal-input-wrap');
            const status = document.getElementById('emailStatus');
            if (this.value.length === 0) {
                wrap.classList.remove('valid', 'invalid');
                status.textContent = '';
            } else if (this.validity.valid) {
                wrap.classList.add('valid');
                wrap.classList.remove('invalid');
                status.innerHTML = '&#10003;';
                status.style.color = '#22c55e';
            } else {
                wrap.classList.add('invalid');
                wrap.classList.remove('valid');
                status.innerHTML = '&#10007;';
                status.style.color = '#ef4444';
            }
        });
    }

    function checkPasswordMatch() {
        const wrap = confirmInput.closest('.modal-input-wrap');
        const status = document.getElementById('confirmStatus');
        if (confirmInput.value.length === 0) {
            wrap.classList.remove('valid', 'invalid');
            status.textContent = '';
        } else if (confirmInput.value === passwordInput.value) {
            wrap.classList.add('valid');
            wrap.classList.remove('invalid');
            status.innerHTML = '&#10003;';
            status.style.color = '#22c55e';
        } else {
            wrap.classList.add('invalid');
            wrap.classList.remove('valid');
            status.innerHTML = '&#10007;';
            status.style.color = '#ef4444';
        }
    }

    if (confirmInput && passwordInput) {
        confirmInput.addEventListener('input', checkPasswordMatch);
        passwordInput.addEventListener('input', checkPasswordMatch);
    }
});

/* ===== CLOSE ON OVERLAY CLICK / ESCAPE ===== */

if (modal) {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && modal.classList.contains('active')) {
        closeModal();
    }
});

/* ===== CSRF TOKEN HELPER ===== */

function getCSRFToken() {
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput) return csrfInput.value;

    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

/* ===== REGISTER HANDLER ===== */

function handleRegister() {
    const name = document.getElementById('regName').value.trim();
    const username = document.getElementById('regUsername').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value.trim();
    const confirm = document.getElementById('regConfirm').value.trim();

    if (!name || !username || !email || !password || !confirm) {
        alert('Please fill in all fields.');
        return;
    }

    if (password !== confirm) {
        alert('Passwords do not match.');
        return;
    }

    fetch('/auth/register/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            name: name,
            username: username,
            email: email,
            password: password,
            disability_status: disabilityStatus,
        }),
    })
    .then(res => res.json().then(data => ({ status: res.status, body: data })))
    .then(({ status, body }) => {
        if (body.success) {
            window.location.href = body.redirect_url;
        } else {
            alert(body.error || 'Registration failed.');
        }
    })
    .catch(() => alert('Network error. Please try again.'));
}

/* ===== LOGIN HANDLER ===== */

function handleLogin() {
    const usernameOrEmail = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value.trim();

    if (!usernameOrEmail || !password) {
        alert('Please fill in all fields.');
        return;
    }

    fetch('/auth/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            username: usernameOrEmail,
            password: password,
        }),
    })
    .then(res => res.json().then(data => ({ status: res.status, body: data })))
    .then(({ status, body }) => {
        if (body.success) {
            window.location.href = body.redirect_url;
        } else {
            alert(body.error || 'Login failed.');
        }
    })
    .catch(() => alert('Network error. Please try again.'));
}
