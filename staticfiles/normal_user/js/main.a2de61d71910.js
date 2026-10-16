let currentFriend = null;
let currentFriendData = null;
let messages = {};
let conversations = [];
let activeChatTab = 'all';
let chatSocket = null;
let presenceSocket = null;
let currentUserId = null;
let notifications = [];
let unreadNotificationCount = 0;
let friendSearchTimeout = null;
let notifSearchTimeout = null;
let notifFilterType = 'all';

const pageTitles = {
    friends: 'Friends', help: 'Help & Support',
    notifications: 'Notifications', settings: 'Settings', profile: 'My Profile'
};

let currentUserData = {};

document.addEventListener('DOMContentLoaded', function () {
    const userMeta = document.getElementById('user-meta');
    if (userMeta) {
        currentUserId = parseInt(userMeta.dataset.userId);
        currentUserData = {
            id: currentUserId,
            name: userMeta.dataset.userName,
            username: userMeta.dataset.userUsername,
            email: userMeta.dataset.userEmail,
            profile_pic: userMeta.dataset.profilePic || '',
        };
    }
    loadChatList();
    connectWebSocket();
    connectPresenceSocket();
    fetchUnreadNotificationCount();
});

function loadChatList(callback) {
    fetch('/chat/api/chat-list/')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                conversations = data.chats.map(c => ({
                    id: c.id,
                    name: c.full_name,
                    role: c.is_asl_user ? 'ASL User' : 'Normal User',
                    color: c.is_asl_user ? '#f59e0b' : '#7c3aed',
                    online: false,
                    preview: c.last_message ? c.last_message.content : '',
                    time: c.last_message ? formatTime(c.last_message.time) : '',
                    unread: c.unread_count || 0,
                    is_asl_user: c.is_asl_user,
                    profile_pic: c.profile_picture_url || '',
                }));
                renderConversations();
                if (callback) callback();
            }
        })
        .catch(() => {});
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    chatSocket = new WebSocket(`${protocol}//${window.location.host}/ws/chat/`);

    chatSocket.onopen = function () {
        console.log('Chat WebSocket connected');
    };

    chatSocket.onerror = function (err) {
        console.error('Chat WebSocket error:', err);
    };

    chatSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        handleWebSocketMessage(data);
    };

    chatSocket.onclose = function (e) {
        console.warn('Chat WebSocket closed (code ' + e.code + '). Reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };
}

function connectPresenceSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    presenceSocket = new WebSocket(`${protocol}//${window.location.host}/ws/presence/`);

    presenceSocket.onopen = function () {
        console.log('Presence WebSocket connected');
    };

    presenceSocket.onerror = function (err) {
        console.error('Presence WebSocket error:', err);
    };

    presenceSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        handlePresenceMessage(data);
    };

    presenceSocket.onclose = function (e) {
        console.warn('Presence WebSocket closed (code ' + e.code + '). Reconnecting...');
        setTimeout(connectPresenceSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    if (data.type === 'new_message') {
        const msg = data.message;
        const friendId = msg.sender_id === currentUserId ? msg.receiver_id : msg.sender_id;

        if (!messages[friendId]) {
            messages[friendId] = [];
        }
        messages[friendId].push(msg);

        if (currentFriend == friendId) {
            renderMessages(friendId);
            markAsRead(friendId);
        }

        updateConversationPreview(friendId, msg);
        updateUnreadCount(friendId);

    } else if (data.type === 'notification') {
        const notif = data.notification;
        notifications.unshift(notif);
        unreadNotificationCount++;
        updateNotificationBadge();
        showNotificationToast(notif);
        const dropdown = document.getElementById('notificationDropdown');
        if (dropdown && dropdown.classList.contains('show')) {
            renderDropdownNotifications();
        }

    } else if (data.type === 'friend_request_sent') {
        unreadNotificationCount++;
        updateNotificationBadge();
        const from = data.from_user;
        showToast(`Friend request from ${from.full_name || from.username}`);
        const notif = data.notification;
        if (notif) {
            notifications.unshift(notif);
        }
        refreshFriendRequestBadge();

    } else if (data.type === 'friend_request_accepted') {
        const by = data.by_user;
        showToast(`${by.full_name || by.username} accepted your friend request!`);
        const notif = data.notification;
        if (notif) {
            notifications.unshift(notif);
        }
        const colContent = document.getElementById('colContent');
        if (colContent && colContent.classList.contains('active')) {
            closeOverlay();
        }
        loadChatList(() => openConversation(by.id));

    } else if (data.type === 'read_receipt') {
        const readBy = data.read_by;
        if (messages[readBy]) {
            messages[readBy].forEach(m => {
                if (m.sender_id === currentUserId && !m.is_read) {
                    m.is_read = true;
                    m.read_at = new Date().toISOString();
                }
            });
            if (currentFriend == readBy) {
                renderMessages(readBy);
            }
        }

    } else if (data.type === 'message_deleted') {
        const msgId = data.message_id;
        for (const friendId in messages) {
            const idx = messages[friendId].findIndex(m => m.id === msgId);
            if (idx !== -1) {
                messages[friendId].splice(idx, 1);
                if (currentFriend == friendId) {
                    renderMessages(friendId);
                }
                break;
            }
        }
    }
}

function handlePresenceMessage(data) {
    if (data.type === 'user_online') {
        const convo = conversations.find(c => c.id == data.user_id);
        if (convo) convo.online = true;
        if (currentFriend == data.user_id) updateChatStatus(true);
        renderConversations();
    } else if (data.type === 'user_offline') {
        const convo = conversations.find(c => c.id == data.user_id);
        if (convo) convo.online = false;
        if (currentFriend == data.user_id) updateChatStatus(false);
        renderConversations();
    } else if (data.type === 'online_users') {
        const ids = data.user_ids || [];
        conversations.forEach(c => {
            c.online = ids.includes(Number(c.id));
        });
        if (currentFriend) {
            const convo = conversations.find(c => c.id == currentFriend);
            if (convo) updateChatStatus(convo.online);
        }
        renderConversations();
    }
}

function updateChatStatus(online) {
    document.getElementById('chatStatus').innerHTML = `
        <span class="status-indicator ${online ? 'online' : 'offline'}"></span>
        <span>${online ? 'Online' : 'Offline'}</span>
    `;
}

function formatTime(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatTimestamp(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function renderConversations() {
    const container = document.getElementById('conversationList');
    let filtered = conversations;
    if (activeChatTab === 'contacts') {
        filtered = conversations.filter(c => !c.is_asl_user);
    } else if (activeChatTab === 'groups') {
        filtered = [];
    }
    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:60px 20px;color:var(--text-light);">
                <i class="far fa-comment-alt" style="font-size:40px;opacity:0.3;display:block;margin-bottom:12px;"></i>
                <div style="font-size:15px;font-weight:500;">No conversations yet</div>
                <div style="font-size:13px;margin-top:4px;">Add friends to start chatting</div>
            </div>
        `;
        return;
    }
    container.innerHTML = filtered.map(c => `
        <div class="conversation-item${currentFriend == c.id ? ' active' : ''}" onclick="openConversation(${c.id})">
            <div class="conversation-avatar" style="background:${c.color};${c.profile_pic ? ' overflow:hidden;' : ''}">
                ${c.profile_pic ? `<img src="${c.profile_pic}" alt="${escapeHtml(c.name)}">` : c.name.charAt(0).toUpperCase()}
                ${c.online ? '<span class="online-dot"></span>' : ''}
            </div>
            <div class="conversation-info">
                <div class="conversation-name">${escapeHtml(c.name)}</div>
                <div class="conversation-preview">${escapeHtml(c.preview)}</div>
            </div>
            <div class="conversation-meta">
                <span class="conversation-time">${c.time}</span>
                ${c.unread > 0 ? `<span class="conversation-unread">${c.unread}</span>` : ''}
            </div>
        </div>
    `).join('');
}

let chatSearchTimeout;
function onChatSearch(value) {
    clearTimeout(chatSearchTimeout);
    chatSearchTimeout = setTimeout(() => {
    const container = document.getElementById('conversationList');
    let filtered = conversations;
    const q = value.toLowerCase().trim();
    if (q) {
        filtered = filtered.filter(c => c.name.toLowerCase().includes(q));
    }
    if (activeChatTab === 'contacts') {
        filtered = filtered.filter(c => !c.is_asl_user);
    } else if (activeChatTab === 'groups') {
        filtered = [];
    }
    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:60px 20px;color:var(--text-light);">
                <i class="fas fa-search" style="font-size:40px;opacity:0.3;display:block;margin-bottom:12px;"></i>
                <div style="font-size:15px;font-weight:500;">No results found</div>
            </div>
        `;
        return;
    }
    container.innerHTML = filtered.map(c => `
        <div class="conversation-item${currentFriend == c.id ? ' active' : ''}" onclick="openConversation(${c.id})">
            <div class="conversation-avatar" style="background:${c.color};${c.profile_pic ? ' overflow:hidden;' : ''}">
                ${c.profile_pic ? `<img src="${c.profile_pic}" alt="${escapeHtml(c.name)}">` : c.name.charAt(0).toUpperCase()}
                ${c.online ? '<span class="online-dot"></span>' : ''}
            </div>
            <div class="conversation-info">
                <div class="conversation-name">${escapeHtml(c.name)}</div>
                <div class="conversation-preview">${escapeHtml(c.preview)}</div>
            </div>
            <div class="conversation-meta">
                <span class="conversation-time">${c.time}</span>
                ${c.unread > 0 ? `<span class="conversation-unread">${c.unread}</span>` : ''}
            </div>
        </div>
    `).join('');
    }, 300);
}

function switchChatTab(el, tab) {
    document.querySelectorAll('.chatlist-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    activeChatTab = tab;
    renderConversations();
}

function openConversation(friendId) {
    const friend = conversations.find(f => f.id == friendId);
    if (!friend) return;
    currentFriend = friendId;
    currentFriendData = friend;

    const avatarEl = document.getElementById('chatAvatar');
    avatarEl.style.background = friend.color;
    avatarEl.style.overflow = friend.profile_pic ? 'hidden' : '';
    avatarEl.innerHTML = friend.profile_pic
        ? `<img src="${friend.profile_pic}" alt="${escapeHtml(friend.name)}">`
        : friend.name.charAt(0).toUpperCase();
    document.getElementById('chatName').textContent = friend.name;
    updateChatStatus(friend.online);

    document.getElementById('chatEmpty').style.display = 'none';
    document.getElementById('chatActive').style.display = 'flex';

    loadMessages(friendId);
    renderConversations();

    if (window.innerWidth <= 768) {
        document.getElementById('chatListPanel').style.display = 'none';
        document.getElementById('chatPanel').classList.add('show');
    }
}

function closeConversation() {
    currentFriend = null;
    currentFriendData = null;
    document.getElementById('chatEmpty').style.display = 'flex';
    document.getElementById('chatActive').style.display = 'none';

    if (window.innerWidth <= 768) {
        document.getElementById('chatListPanel').style.display = '';
        document.getElementById('chatPanel').classList.remove('show');
    }
}

function loadMessages(friendId) {
    fetch(`/chat/api/messages/?friend_id=${friendId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                messages[friendId] = data.messages;
                renderMessages(friendId);
                markAsRead(friendId);
            }
        })
        .catch(() => {});
}

function markAsRead(friendId) {
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            type: 'mark_read',
            sender_id: friendId,
        }));
    }
    const convo = conversations.find(c => c.id == friendId);
    if (convo) {
        convo.unread = 0;
        renderConversations();
    }
}

function renderMessages(friendId) {
    const area = document.getElementById('messagesArea');
    const msgs = messages[friendId] || [];
    if (msgs.length === 0) {
        area.innerHTML = `
            <div style="text-align:center;padding:60px 20px;color:var(--text-light);flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                <i class="far fa-comment-alt" style="font-size:48px;opacity:0.25;display:block;margin-bottom:12px;"></i>
                <div style="font-size:15px;font-weight:500;">No messages yet</div>
                <div style="font-size:13px;margin-top:4px;">Say hello to start the conversation!</div>
            </div>
        `;
        return;
    }
    area.innerHTML = msgs.map(m => renderMessageHtml(m)).join('');
    area.scrollTop = area.scrollHeight;
}

function renderMessageHtml(m) {
    const isMine = m.is_mine || m.sender_id === currentUserId;
    const timeStr = formatTimestamp(m.timestamp);
    const displayType = m.display_type || m.message_type;

    let contentHtml = '';
    if (displayType === 'gesture' && m.display_gesture) {
        contentHtml = renderGestureContent(m.display_gesture);
    } else if (displayType === 'asl' && m.display_asl) {
        contentHtml = renderASLContent(m.display_asl, m.display_content);
    } else {
        const text = m.display_content || m.content || '';
        contentHtml = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    }

    const receiptHtml = isMine ? renderReadReceipt(m) : '';

    return `
        <div class="message ${isMine ? 'sent' : 'received'}">
            <div class="message-bubble-wrap">
                ${contentHtml}
                <div class="message-actions">
                    <button class="message-action-btn" onclick="copyMessage(${m.id})" title="Copy"><i class="fas fa-copy"></i></button>
                    ${isMine ? `<button class="message-action-btn delete" onclick="deleteMessage(${m.id})" title="Delete"><i class="fas fa-trash"></i></button>` : ''}
                </div>
            </div>
            <div class="message-footer">
                <span class="message-time">${timeStr}</span>
                ${receiptHtml}
            </div>
        </div>
    `;
}

function renderGestureContent(gesture) {
    return `
        <div class="asl-gesture-card">
            ${gesture.video_url
                ? (/\.(jpe?g|png|gif|webp|bmp|svg)(\?.*)?$/i.test(gesture.video_url)
                    ? `<img src="${gesture.video_url}" style="width:100%;max-height:140px;border-radius:8px;">`
                    : `<video src="${gesture.video_url}" style="width:100%;max-height:140px;border-radius:8px;" controls playsinline></video>`)
                : `<div class="gesture-emoji">🤟</div>`}
        </div>
    `;
}

function renderASLContent(aslData, translation) {
    const symbolsHtml = aslData
        .map(s => {
            if (s.char === ' ') {
                return `<div class="asl-symbol-space"></div>`;
            }
            const imgUrl = s.image_url;
            return imgUrl
                ? `<div class="asl-symbol"><img src="${imgUrl}" class="asl-symbol-msg-img" alt="${escapeHtml(s.char)}"></div>`
                : `<div class="asl-symbol"><span class="asl-symbol-text">${escapeHtml(s.char)}</span></div>`;
        }).join('');
    return `
        <div class="message-bubble asl-message-bubble">
            <div class="asl-symbols-row">${symbolsHtml}</div>
            ${translation ? `<div class="asl-translation">"${escapeHtml(translation)}"</div>` : ''}
        </div>
    `;
}

function renderReadReceipt(m) {
    if (m.is_read) {
        return `<span class="read-receipt read"><i class="fas fa-check-double"></i></span>`;
    }
    return `<span class="read-receipt sent"><i class="fas fa-check"></i></span>`;
}

function sendMessage() {
    if (!currentFriend) return;
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    if (!text) return;

    const receiver = conversations.find(c => c.id == currentFriend);
    const receiverIsASL = receiver ? receiver.is_asl_user : false;

    sendViaWebSocket(currentFriend, text, 'text', null, null);
    input.value = '';
}

function sendViaWebSocket(receiverId, content, messageType, aslContent, gestureId) {
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            type: 'chat_message',
            receiver_id: receiverId,
            content: content,
            message_type: messageType,
            asl_content: aslContent,
            gesture_id: gestureId,
        }));
    } else {
        fetch('/chat/api/send/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
            body: JSON.stringify({
                receiver_id: receiverId,
                content: content,
                message_type: messageType,
                asl_content: aslContent,
                gesture_id: gestureId,
            }),
        }).then(r => r.json()).then(data => {
            if (data.success) {
                if (!messages[receiverId]) messages[receiverId] = [];
                messages[receiverId].push(data.msg);
                if (currentFriend == receiverId) renderMessages(receiverId);
                updateConversationPreview(receiverId, data.msg);
            }
        }).catch(() => {});
    }
}

function copyMessage(msgId) {
    const content = getMessageContent(msgId);
    if (content) {
        navigator.clipboard.writeText(content).then(() => {
            showToast('Message copied to clipboard');
        }).catch(() => {
            showToast('Failed to copy', true);
        });
        return;
    }
    fetch('/chat/api/copy/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ message_id: msgId }),
    }).then(r => r.json()).then(data => {
        if (data.success && data.content) {
            navigator.clipboard.writeText(data.content).then(() => {
                showToast('Message copied to clipboard');
            });
        }
    }).catch(() => {
        showToast('Failed to copy', true);
    });
}

function getMessageContent(msgId) {
    for (const fid in messages) {
        const m = messages[fid].find(msg => msg.id === msgId);
        if (m) return m.display_content || m.content || '';
    }
    return '';
}

function deleteMessage(msgId) {
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            type: 'delete_message',
            message_id: msgId,
        }));
    }
    fetch('/chat/api/delete/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ message_id: msgId }),
    }).then(r => r.json()).then(data => {
        if (data.success) {
            for (const fid in messages) {
                const idx = messages[fid].findIndex(m => m.id === msgId);
                if (idx !== -1) {
                    messages[fid].splice(idx, 1);
                    if (currentFriend == fid) renderMessages(fid);
                    break;
                }
            }
            showToast('Message deleted');
        }
    }).catch(() => {});
}

function updateConversationPreview(friendId, msg) {
    const convo = conversations.find(c => c.id == friendId);
    if (!convo) return;
    const text = msg.display_content || msg.content || '';
    const type = msg.display_type || msg.message_type;
    if (type === 'asl') {
        convo.preview = '[ASL Symbols]';
    } else if (type === 'gesture') {
        convo.preview = '[Gesture]';
    } else {
        convo.preview = text;
    }
    convo.time = 'Just now';
    if (msg.sender_id !== currentUserId && friendId !== currentFriend) {
        convo.unread = (convo.unread || 0) + 1;
    }
    renderConversations();
}

function updateUnreadCount(friendId) {
    const convo = conversations.find(c => c.id == friendId);
    if (convo && friendId !== currentFriend) {
        convo.unread = (convo.unread || 0) + 1;
        renderConversations();
    }
}

function handleKey(e) {
    if (e.key === 'Enter') sendMessage();
}

function toggleSidebar() {
    const overlay = document.getElementById('sidebarOverlay');
    const sidebar = document.getElementById('sidebar');
    const hamburger = document.getElementById('topbarHamburger');
    overlay?.classList.toggle('open');
    sidebar?.classList.toggle('open');
    const icon = hamburger?.querySelector('i');
    if (icon) {
        icon.className = sidebar?.classList.contains('open') ? 'fas fa-times' : 'fas fa-bars';
    }
    document.body.style.overflow = sidebar?.classList.contains('open') ? 'hidden' : '';
}

function closeSidebar() {
    document.getElementById('sidebarOverlay')?.classList.remove('open');
    document.getElementById('sidebar')?.classList.remove('open');
    const hamburger = document.getElementById('topbarHamburger');
    const icon = hamburger?.querySelector('i');
    if (icon) icon.className = 'fas fa-bars';
    document.body.style.overflow = '';
}

function showPage(page) {
    closeSidebar();
    document.querySelectorAll('.sidebar-nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.sidebar-nav-item[data-page="${page}"]`)?.classList.add('active');

    const mainContent = document.getElementById('mainContent');
    const colContent = document.getElementById('colContent');

    if (page === 'chat' && !mainContent.classList.contains('content-active')) {
        return;
    }

    if (page === 'chat') {
        colContent.classList.remove('active');
        setTimeout(() => {
            mainContent.classList.remove('content-active');
            colContent.innerHTML = '';
        }, 300);
        return;
    }

    if (colContent.classList.contains('active')) {
        colContent.classList.remove('active');
        setTimeout(() => {
            mainContent.classList.add('content-active');
            colContent.innerHTML = getPageContent(page);
            void colContent.offsetHeight;
            colContent.classList.add('active');
            loadPageContent(page);
        }, 150);
    } else {
        mainContent.classList.add('content-active');
        colContent.innerHTML = getPageContent(page);
        void colContent.offsetHeight;
        colContent.classList.add('active');
        loadPageContent(page);
    }

    if (window.innerWidth <= 1024) {
        closeSidebar();
    }
}

function closeOverlay() {
    const mainContent = document.getElementById('mainContent');
    const colContent = document.getElementById('colContent');
    mainContent.classList.remove('content-active');
    colContent.classList.remove('active');
    colContent.innerHTML = '';
    document.querySelectorAll('.sidebar-nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('.sidebar-nav-item[data-page="chat"]')?.classList.add('active');
}

function getPageContent(page) {
    switch (page) {
        case 'friends': return friendsPageHTML();
        case 'help': return helpPageHTML();
        case 'notifications': return notificationsPageHTML();
        case 'settings': return settingsPageHTML();
        case 'profile': return profilePageHTML();
        default: return '<p>Page not found</p>';
    }
}

function loadPageContent(page) {
    if (page === 'help') {
        setTimeout(loadHelpTickets, 100);
    }
    if (page === 'friends') {
        setTimeout(loadFriendList, 100);
    }
    if (page === 'notifications') {
        setTimeout(() => {
            loadNotifications();
            fetchUnreadNotificationCount();
        }, 100);
    }
}

function friendsPageHTML() {
    return `
        <div class="page-overlay-header">
            <button class="page-overlay-back" onclick="closeOverlay()"><i class="fas fa-arrow-left"></i></button>
            <h2 class="page-overlay-title">Friends</h2>
        </div>
        <div class="search-box">
            <input type="text" class="form-input" id="friend-search-input" placeholder="Search users..." oninput="searchUsers(this.value)">
            <button class="btn btn-primary" onclick="searchUsers(document.getElementById('friend-search-input').value)"><i class="fas fa-search"></i></button>
        </div>
        <div id="friend-search-results" style="display:none;max-width:600px;margin-bottom:12px;"></div>
        <div class="tabs">
            <button class="tab active" onclick="switchFriendsTab('list', this)">My Friends (<span id="friend-count">0</span>)</button>
            <button class="tab" onclick="switchFriendsTab('requests', this)">Requests</button>
        </div>
        <div id="friends-content" style="display:flex;flex-direction:column;gap:10px;max-width:600px;">
            <div style="text-align:center;padding:40px;color:var(--text-light);">Loading...</div>
        </div>
    `;
}

function switchFriendsTab(tab, btn) {
    document.querySelectorAll('#colContent .tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    if (tab === 'list') {
        loadFriendList();
    } else {
        loadPendingRequests();
    }
}

function searchUsers(query) {
    clearTimeout(friendSearchTimeout);
    const resultsDiv = document.getElementById('friend-search-results');
    if (!query.trim()) {
        resultsDiv.style.display = 'none';
        resultsDiv.innerHTML = '';
        document.getElementById('friends-content').style.display = 'flex';
        return;
    }
    friendSearchTimeout = setTimeout(() => {
        fetch(`/friends/search/?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    renderSearchResults(data.users);
                }
            })
            .catch(() => {});
    }, 300);
}

function renderSearchResults(users) {
    const resultsDiv = document.getElementById('friend-search-results');
    const contentDiv = document.getElementById('friends-content');
    if (users.length === 0) {
        resultsDiv.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-light);font-size:13px;">No users found</div>';
        resultsDiv.style.display = 'block';
        contentDiv.style.display = 'none';
        return;
    }
    resultsDiv.style.display = 'block';
    contentDiv.style.display = 'none';
    resultsDiv.innerHTML = users.map(u => {
        let actionBtn = '';
        if (u.friend_status === 'accepted') {
            actionBtn = '<span style="font-size:12px;color:var(--green);font-weight:500;">✓ Friends</span>';
        } else if (u.friend_status === 'pending' && u.sent_by_me) {
            actionBtn = `<button class="btn btn-outline btn-sm" onclick="cancelFriendRequest(${u.friend_request_id})" style="font-size:11px;padding:4px 8px;">Cancel Request</button>`;
        } else if (u.friend_status === 'pending' && !u.sent_by_me) {
            actionBtn = `<span style="font-size:12px;color:var(--orange);font-weight:500;">Pending</span>`;
        } else if (u.friend_status === 'rejected') {
            actionBtn = `<button class="btn btn-primary btn-sm" onclick="sendFriendRequest(${u.id})" style="font-size:11px;padding:4px 8px;"><i class="fas fa-user-plus"></i> Add Friend</button>`;
        } else {
            actionBtn = `<button class="btn btn-primary btn-sm" onclick="sendFriendRequest(${u.id})" style="font-size:11px;padding:4px 8px;"><i class="fas fa-user-plus"></i> Add Friend</button>`;
        }
        return `
            <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--bg);border-radius:12px;border:1px solid var(--border);">
                <div style="width:40px;height:40px;border-radius:50%;background:${u.is_asl_user ? '#f59e0b' : '#7c3aed'};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:16px;flex-shrink:0;">${(u.full_name || 'U').charAt(0).toUpperCase()}</div>
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:600;font-size:14px;">${escapeHtml(u.full_name)}</div>
                    <div style="font-size:12px;color:var(--text-light);">@${escapeHtml(u.username)} ${u.is_asl_user ? '• ASL User' : '• Normal User'}</div>
                </div>
                ${actionBtn}
            </div>
        `;
    }).join('');
}

function sendFriendRequest(userId) {
    fetch('/friends/send/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ user_id: userId }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Friend request sent!');
            searchUsers(document.getElementById('friend-search-input').value);
        } else {
            showToast(data.error || 'Failed to send request', true);
        }
    })
    .catch(() => showToast('Network error', true));
}

function cancelFriendRequest(requestId) {
    fetch('/friends/cancel/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ request_id: requestId }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Request cancelled');
            searchUsers(document.getElementById('friend-search-input').value);
            loadFriendList();
        } else {
            showToast(data.error || 'Failed to cancel', true);
        }
    })
    .catch(() => showToast('Network error', true));
}

function loadFriendList() {
    const contentDiv = document.getElementById('friends-content');
    contentDiv.style.display = 'flex';
    document.getElementById('friend-search-results').style.display = 'none';
    contentDiv.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-light);">Loading...</div>';

    fetch('/friends/list/')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const friends = data.friends;
                document.getElementById('friend-count').textContent = friends.length;
                if (friends.length === 0) {
                    contentDiv.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-light);">No friends yet. Search for users to add friends!</div>';
                    return;
                }
                contentDiv.innerHTML = friends.map(f => `
                    <div style="display:flex;align-items:center;gap:14px;padding:14px 18px;background:var(--bg);border-radius:12px;border:1px solid var(--border);cursor:pointer;" onclick="quickOpenChat(${f.id})">
                        <div style="width:44px;height:44px;border-radius:50%;background:${f.is_asl_user ? '#f59e0b' : '#7c3aed'};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:18px;flex-shrink:0;overflow:hidden;">
                            ${(f.full_name || 'F').charAt(0).toUpperCase()}
                        </div>
                        <div style="flex:1;">
                            <div style="font-weight:600;font-size:14px;">${escapeHtml(f.full_name)}</div>
                            <div style="font-size:12px;color:var(--text-light);">${f.is_asl_user ? 'ASL User' : 'Normal User'}</div>
                        </div>
                        <button class="btn btn-primary" style="padding:6px 12px;font-size:12px;" onclick="event.stopPropagation();quickOpenChat(${f.id})"><i class="far fa-comment-alt"></i></button>
                    </div>
    `).join('');
            }
        })
        .catch(() => {
            contentDiv.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-light);">Failed to load friends</div>';
        });
}

function loadPendingRequests() {
    const contentDiv = document.getElementById('friends-content');
    contentDiv.style.display = 'flex';
    document.getElementById('friend-search-results').style.display = 'none';
    contentDiv.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-light);">Loading...</div>';

    fetch('/friends/pending/')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const requests = data.requests;
                let html = '';
                if (requests.length === 0) {
                    html = '<div style="text-align:center;padding:40px;color:var(--text-light);">No pending requests</div>';
                } else {
                    html = '<div style="font-size:13px;color:var(--text-secondary);margin-bottom:8px;font-weight:500;">Received Requests</div>';
                    html += requests.map(r => `
                        <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--bg);border-radius:12px;border:1px solid var(--border);">
                            <div style="width:40px;height:40px;border-radius:50%;background:${r.from_user.is_asl_user ? '#f59e0b' : '#7c3aed'};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:16px;flex-shrink:0;">${(r.from_user.full_name || 'U').charAt(0).toUpperCase()}</div>
                            <div style="flex:1;min-width:0;">
                                <div style="font-weight:600;font-size:14px;">${escapeHtml(r.from_user.full_name)}</div>
                                <div style="font-size:12px;color:var(--text-light);">@${escapeHtml(r.from_user.username)}</div>
                            </div>
                            <button class="btn btn-primary btn-sm" onclick="acceptFriendRequest(${r.id})" style="font-size:11px;padding:4px 10px;"><i class="fas fa-check"></i> Accept</button>
                            <button class="btn btn-outline btn-sm" onclick="rejectFriendRequest(${r.id})" style="font-size:11px;padding:4px 10px;color:var(--red);border-color:var(--red);"><i class="fas fa-times"></i> Reject</button>
                        </div>
                    `).join('');
                }

                fetch('/friends/sent/')
                    .then(r2 => r2.json())
                    .then(data2 => {
                        if (data2.success && data2.sent_requests.length > 0) {
                            html += '<div style="font-size:13px;color:var(--text-secondary);margin:16px 0 8px;font-weight:500;">Sent Requests</div>';
                            html += data2.sent_requests.map(r => `
                                <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--bg);border-radius:12px;border:1px solid var(--border);">
                                    <div style="width:40px;height:40px;border-radius:50%;background:${r.to_user.is_asl_user ? '#f59e0b' : '#7c3aed'};display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:16px;flex-shrink:0;">${(r.to_user.full_name || 'U').charAt(0).toUpperCase()}</div>
                                    <div style="flex:1;min-width:0;">
                                        <div style="font-weight:600;font-size:14px;">${escapeHtml(r.to_user.full_name)}</div>
                                        <div style="font-size:12px;color:var(--text-light);">@${escapeHtml(r.to_user.username)}</div>
                                    </div>
                                    <span style="font-size:11px;color:var(--orange);">Pending</span>
                                    <button class="btn btn-outline btn-sm" onclick="cancelFriendRequest(${r.id})" style="font-size:11px;padding:4px 8px;">Cancel</button>
                                </div>
                            `).join('');
                        }
                        contentDiv.innerHTML = html;
                    })
                    .catch(() => {});
            }
        })
        .catch(() => {
            contentDiv.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-light);">Failed to load requests</div>';
        });
}

function acceptFriendRequest(requestId) {
    fetch('/friends/accept/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ request_id: requestId }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Friend request accepted!');
            loadFriendList();
            loadChatList();
        } else {
            showToast(data.error || 'Failed to accept', true);
        }
    })
    .catch(() => showToast('Network error', true));
}

function rejectFriendRequest(requestId) {
    fetch('/friends/reject/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ request_id: requestId }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Friend request rejected');
            loadPendingRequests();
        } else {
            showToast(data.error || 'Failed to reject', true);
        }
    })
    .catch(() => showToast('Network error', true));
}

function fetchUnreadNotificationCount() {
    fetch('/notifications/unread-count/')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                unreadNotificationCount = data.count;
                updateNotificationBadge();
            }
        })
        .catch(() => {});
}

function updateNotificationBadge() {
    const sidebarBadge = document.getElementById('notificationBadge');
    const bellBadge = document.getElementById('bellBadge');
    if (unreadNotificationCount > 0) {
        const displayCount = unreadNotificationCount > 10 ? '10+' : unreadNotificationCount;
        if (sidebarBadge) {
            sidebarBadge.textContent = unreadNotificationCount > 99 ? '99+' : unreadNotificationCount;
            sidebarBadge.style.display = 'flex';
        }
        if (bellBadge) {
            bellBadge.textContent = displayCount;
            bellBadge.style.display = 'flex';
        }
    } else {
        if (sidebarBadge) sidebarBadge.style.display = 'none';
        if (bellBadge) bellBadge.style.display = 'none';
    }
}

function toggleNotificationDropdown() {
    const dropdown = document.getElementById('notificationDropdown');
    if (dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
        return;
    }
    loadDropdownNotifications();
    dropdown.classList.add('show');
}

function loadDropdownNotifications() {
    fetch('/notifications/?limit=20')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                notifications = data.notifications;
                renderDropdownNotifications();
            }
        })
        .catch(() => {});
}

function renderDropdownNotifications() {
    const list = document.getElementById('notificationDropdownList');
    if (!list) return;
    if (notifications.length === 0) {
        list.innerHTML = `
            <div class="notif-dropdown-empty">
                <i class="far fa-bell"></i>
                <span>No notifications</span>
            </div>
        `;
        return;
    }
    list.innerHTML = notifications.map(n => {
        const icon = getNotificationIcon(n.type, n.icon);
        const timeAgo = timeSince(n.created_at);
        return `
            <div class="notification-dropdown-item${n.is_read ? '' : ' unread'}" data-id="${n.id}" onclick="handleDropdownNotificationClick(${n.id}, '${n.type}', ${n.related_user_id || 'null'})">
                <div class="notification-dropdown-icon">${icon}</div>
                <div class="notification-dropdown-content">
                    <div class="notification-dropdown-title-text">${escapeHtml(n.title)}</div>
                    ${n.message ? `<div class="notification-dropdown-message">${escapeHtml(n.message)}</div>` : ''}
                    <div class="notification-dropdown-time">${timeAgo}</div>
                </div>
                <div class="notification-dropdown-item-actions">
                    <button class="notification-dropdown-item-btn" onclick="event.stopPropagation();markSingleNotificationRead(${n.id})" title="Mark as read"><i class="fas fa-check"></i></button>
                    <button class="notification-dropdown-item-btn delete" onclick="event.stopPropagation();deleteSingleNotification(${n.id})" title="Delete"><i class="fas fa-trash"></i></button>
                </div>
            </div>
        `;
    }).join('');
}

function handleDropdownNotificationClick(notifId, type, relatedUserId) {
    fetch('/notifications/mark-read/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ notification_id: notifId }),
    }).catch(() => {});
    const notif = notifications.find(n => n.id === notifId);
    if (notif) notif.is_read = true;
    if (unreadNotificationCount > 0) unreadNotificationCount--;
    updateNotificationBadge();
    renderDropdownNotifications();

    const dropdown = document.getElementById('notificationDropdown');
    dropdown.classList.remove('show');

    if (type === 'message' && relatedUserId) {
        closeOverlay();
        loadChatList(() => openConversation(relatedUserId));
    } else if (type === 'friend_accepted' && relatedUserId) {
        closeOverlay();
        loadChatList(() => openConversation(relatedUserId));
    } else if (type === 'friend_request' || type === 'friend_rejected') {
        showPage('friends');
    } else if (type.startsWith('support')) {
        showPage('help');
    } else if (type.startsWith('new_gesture') || type === 'new_gesture_category') {
        showPage('settings');
    }
}

function markSingleNotificationRead(notifId) {
    fetch('/notifications/mark-read/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ notification_id: notifId }),
    }).then(r => r.json()).then(data => {
        if (data.success) {
            const notif = notifications.find(n => n.id === notifId);
            if (notif) notif.is_read = true;
            if (unreadNotificationCount > 0) unreadNotificationCount--;
            updateNotificationBadge();
            renderDropdownNotifications();
        }
    }).catch(() => {});
}

function deleteSingleNotification(notifId) {
    fetch('/notifications/delete/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ notification_id: notifId }),
    }).then(r => r.json()).then(data => {
        if (data.success) {
            const notif = notifications.find(n => n.id === notifId);
            if (notif && !notif.is_read && unreadNotificationCount > 0) unreadNotificationCount--;
            notifications = notifications.filter(n => n.id !== notifId);
            updateNotificationBadge();
            renderDropdownNotifications();
        }
    }).catch(() => {});
}

function confirmDeleteAllNotifications() {
    if (!confirm('Delete all notifications? This cannot be undone.')) return;
    fetch('/notifications/delete-all/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
    }).then(r => r.json()).then(data => {
        if (data.success) {
            notifications = [];
            unreadNotificationCount = 0;
            updateNotificationBadge();
            renderDropdownNotifications();
            showToast('All notifications deleted');
        }
    }).catch(() => {});
}

function refreshFriendRequestBadge() {
    const pendingEl = document.getElementById('friend-count');
    if (pendingEl) {
        fetch('/friends/pending/')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const count = data.requests.length;
                    const badge = document.getElementById('friendRequestBadge');
                    if (badge) {
                        if (count > 0) {
                            badge.textContent = count;
                            badge.style.display = 'flex';
                        } else {
                            badge.style.display = 'none';
                        }
                    }
                }
            })
            .catch(() => {});
    }
}

function showNotificationToast(notif) {
    const toast = document.getElementById('toast');
    const msgEl = document.getElementById('toastMessage');
    if (!toast || !msgEl) return;
    const icon = getNotificationIcon(notif.type, notif.icon);
    msgEl.innerHTML = icon + ' ' + escapeHtml(notif.title);
    toast.className = 'toast show';
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('show'), 4000);
}

function loadNotifications(search, filterType) {
    const container = document.getElementById('notifications-list');
    if (!container) return;
    container.innerHTML = `
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:40px;color:var(--primary);margin-bottom:16px;"><i class="fas fa-spinner fa-spin"></i></div>
            <div style="font-size:16px;font-weight:600;color:var(--text-secondary);">Loading notifications...</div>
        </div>
    `;
    let url = '/notifications/?limit=100';
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (filterType && filterType !== 'all') url += `&type=${encodeURIComponent(filterType)}`;
    fetch(url)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                notifications = data.notifications;
                renderNotifications();
            }
        })
        .catch(() => {});
}

function renderNotifications() {
    const container = document.getElementById('notifications-list');
    if (!container) return;
    if (notifications.length === 0) {
        container.innerHTML = `
            <div style="text-align:center;padding:60px 20px;">
                <div style="font-size:48px;color:var(--text-light);opacity:0.3;margin-bottom:12px;"><i class="far fa-bell"></i></div>
                <div style="font-size:16px;font-weight:600;color:var(--text-secondary);">No notifications found</div>
            </div>
        `;
        return;
    }
    container.innerHTML = notifications.map(n => {
        const icon = getNotificationIcon(n.type, n.icon);
        const timeAgo = timeSince(n.created_at);
        return `
            <div class="notification-item${n.is_read ? '' : ' unread'}" data-id="${n.id}">
                <button class="notification-delete-btn" onclick="event.stopPropagation();deletePageNotification(${n.id})" title="Delete">
                    <i class="fas fa-times"></i>
                </button>
                <div class="notification-icon">${icon}</div>
                <div class="notification-content" onclick="handleNotificationClick(${n.id}, '${n.type}', ${n.related_user_id || 'null'})">
                    <div class="notification-title">${escapeHtml(n.title)}</div>
                    ${n.message ? `<div class="notification-message">${escapeHtml(n.message)}</div>` : ''}
                    <div class="notification-time">${timeAgo}</div>
                </div>
                ${n.is_read ? '' : '<div class="notification-dot"></div>'}
            </div>
        `;
    }).join('');
}

function handleNotificationClick(notifId, type, relatedUserId) {
    fetch('/notifications/mark-read/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ notification_id: notifId }),
    }).catch(() => {});
    const notif = notifications.find(n => n.id === notifId);
    if (notif) notif.is_read = true;
    if (unreadNotificationCount > 0) unreadNotificationCount--;
    updateNotificationBadge();
    renderNotifications();
    closeOverlay();
    if (type === 'message' && relatedUserId) {
        loadChatList(() => openConversation(relatedUserId));
    } else if (type === 'friend_accepted' && relatedUserId) {
        loadChatList(() => openConversation(relatedUserId));
    } else if (type === 'friend_request' || type === 'friend_rejected') {
        showPage('friends');
    } else if (type.startsWith('support')) {
        showPage('help');
    } else if (type.startsWith('new_gesture') || type === 'new_gesture_category') {
        showPage('settings');
    }
}

function deletePageNotification(notifId) {
    fetch('/notifications/delete/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ notification_id: notifId }),
    }).then(r => r.json()).then(data => {
        if (data.success) {
            const notif = notifications.find(n => n.id === notifId);
            if (notif && !notif.is_read && unreadNotificationCount > 0) unreadNotificationCount--;
            notifications = notifications.filter(n => n.id !== notifId);
            updateNotificationBadge();
            renderNotifications();
        }
    }).catch(() => {});
}

function getNotificationIcon(type, icon) {
    if (icon) return `<i class="${icon}"></i>`;
    const icons = {
        'friend_request': '<i class="fas fa-user-plus" style="color:var(--primary)"></i>',
        'friend_accepted': '<i class="fas fa-handshake" style="color:var(--green)"></i>',
        'friend_rejected': '<i class="fas fa-user-times" style="color:var(--red)"></i>',
        'message': '<i class="far fa-comment-alt" style="color:var(--primary)"></i>',
        'contact_form': '<i class="fas fa-envelope" style="color:var(--primary)"></i>',
        'support_request': '<i class="fas fa-headset" style="color:var(--primary)"></i>',
        'support_response': '<i class="fas fa-reply" style="color:var(--green)"></i>',
        'support_video_response': '<i class="fas fa-video" style="color:var(--green)"></i>',
        'system': '<i class="fas fa-info-circle" style="color:var(--text-secondary)"></i>',
        'system_announcement': '<i class="fas fa-bullhorn" style="color:var(--primary)"></i>',
        'feature_announcement': '<i class="fas fa-star" style="color:var(--orange)"></i>',
        'maintenance': '<i class="fas fa-tools" style="color:var(--orange)"></i>',
        'profile_update': '<i class="fas fa-user-edit" style="color:var(--primary)"></i>',
        'password_change': '<i class="fas fa-lock" style="color:var(--green)"></i>',
        'new_gesture': '<i class="fas fa-hand-peace" style="color:var(--primary)"></i>',
        'new_gesture_category': '<i class="fas fa-folder-plus" style="color:var(--primary)"></i>',
    };
    return icons[type] || '<i class="fas fa-bell" style="color:var(--text-light)"></i>';
}

function timeSince(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    if (diff < 604800000) return Math.floor(diff / 86400000) + 'd ago';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function markAllNotificationsRead() {
    fetch('/notifications/mark-all-read/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            notifications.forEach(n => n.is_read = true);
            unreadNotificationCount = 0;
            updateNotificationBadge();
            renderNotifications();
            renderDropdownNotifications();
        }
    })
    .catch(() => {});
}

function notificationsPageHTML() {
    return `
        <div class="page-overlay-header">
            <button class="page-overlay-back" onclick="closeOverlay()"><i class="fas fa-arrow-left"></i></button>
            <h2 class="page-overlay-title">Notifications</h2>
            <div class="notification-page-actions">
                <button class="btn btn-outline btn-sm" onclick="markAllNotificationsRead()" style="font-size:11px;padding:4px 10px;">
                    <i class="fas fa-check-double"></i> Mark All Read
                </button>
                <button class="btn btn-outline btn-sm" onclick="confirmDeleteAllNotifications()" style="font-size:11px;padding:4px 10px;color:var(--red);border-color:var(--red);">
                    <i class="fas fa-trash"></i> Delete All
                </button>
            </div>
        </div>
        <div class="notification-search-box">
            <input type="text" class="form-input" id="notif-search-input" placeholder="Search notifications..." oninput="onNotificationSearch(this.value)">
        </div>
        <div class="notification-filter-tabs">
            <button class="notification-filter-tab active" onclick="filterNotifications('all', this)">All</button>
            <button class="notification-filter-tab" onclick="filterNotifications('messages', this)">Messages</button>
            <button class="notification-filter-tab" onclick="filterNotifications('friend', this)">Friend Requests</button>
            <button class="notification-filter-tab" onclick="filterNotifications('support', this)">Support</button>
            <button class="notification-filter-tab" onclick="filterNotifications('system', this)">System</button>
            <button class="notification-filter-tab" onclick="filterNotifications('gesture', this)">Gestures</button>
        </div>
        <div id="notifications-list" style="max-width:600px;">
            <div style="text-align:center;padding:40px;color:var(--text-light);">Loading...</div>
        </div>
    `;
}

function onNotificationSearch(value) {
    clearTimeout(notifSearchTimeout);
    notifSearchTimeout = setTimeout(() => {
        loadNotifications(value.trim(), notifFilterType);
    }, 300);
}

function filterNotifications(type, btn) {
    document.querySelectorAll('.notification-filter-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    notifFilterType = type;
    const searchVal = document.getElementById('notif-search-input')?.value?.trim() || '';
    loadNotifications(searchVal, type);
}

/* Close notification dropdown when clicking outside */
document.addEventListener('click', function(e) {
    const wrapper = document.getElementById('topbarNotifWrapper');
    const dropdown = document.getElementById('notificationDropdown');
    if (wrapper && dropdown && !wrapper.contains(e.target)) {
        dropdown.classList.remove('show');
    }
});

function helpPageHTML() {
    return `
        <div class="page-overlay-header">
            <button class="page-overlay-back" onclick="closeOverlay()"><i class="fas fa-arrow-left"></i></button>
            <h2 class="page-overlay-title">Help & Support</h2>
        </div>
        <div class="card" style="max-width:600px;">
            <div class="card-title"><i class="far fa-question-circle" style="color:var(--primary);"></i>Submit a Help Request</div>
            <div class="form-group">
                <label class="form-label">Subject (optional)</label>
                <input type="text" class="form-input" id="help-subject" placeholder="Brief title for your request...">
            </div>
            <div class="form-group">
                <label class="form-label">Describe your issue</label>
                <textarea class="form-textarea" id="help-description" placeholder="Describe your issue or question in detail..."></textarea>
            </div>
            <button class="btn btn-primary" onclick="submitHelpRequest()">
                <i class="far fa-paper-plane"></i> Submit Request
            </button>
        </div>
        <div class="card" style="max-width:600px;">
            <div class="card-title" style="display:flex;align-items:center;gap:8px">
                <i class="far fa-list-alt" style="color:var(--primary);"></i> Your Help Requests
                <button class="btn btn-outline btn-sm" style="margin-left:auto" onclick="loadHelpTickets()">
                    <i class="fas fa-sync"></i> Refresh
                </button>
            </div>
            <div id="help-tickets-list">
                <p style="color:var(--text-light);font-size:14px;">Loading...</p>
            </div>
        </div>
    `;
}

function submitHelpRequest() {
    const subject = document.getElementById('help-subject').value.trim();
    const description = document.getElementById('help-description').value.trim();
    if (!description) {
        showToast('Please describe your issue.', true);
        return;
    }
    const btn = document.querySelector('.btn-primary[onclick="submitHelpRequest()"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    fetch('/support/create/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({
            subject: subject,
            issue_description: description,
        }),
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i class="far fa-paper-plane"></i> Submit Request';
        if (data.success) {
            showToast('Help request submitted!');
            document.getElementById('help-subject').value = '';
            document.getElementById('help-description').value = '';
            loadHelpTickets();
        } else {
            showToast(data.error || 'Failed to submit', true);
        }
    })
    .catch(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="far fa-paper-plane"></i> Submit Request';
        showToast('Network error', true);
    });
}

function loadHelpTickets() {
    const container = document.getElementById('help-tickets-list');
    if (!container) return;
    container.innerHTML = '<p style="color:var(--text-light);font-size:14px;">Loading...</p>';
    fetch('/support/list/')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                renderHelpTickets(data.tickets);
            } else {
                container.innerHTML = '<p style="color:var(--text-light);font-size:14px;">Failed to load tickets.</p>';
            }
        })
        .catch(() => {
            container.innerHTML = '<p style="color:var(--text-light);font-size:14px;">Network error.</p>';
        });
}

function renderHelpTickets(tickets) {
    const container = document.getElementById('help-tickets-list');
    if (!tickets || tickets.length === 0) {
        container.innerHTML = '<p style="color:var(--text-light);font-size:14px;text-align:center;padding:20px;">No help requests yet</p>';
        return;
    }
    container.innerHTML = tickets.map(t => {
        const statusLabels = { open: 'OPEN', in_progress: 'IN PROGRESS', resolved: 'RESOLVED', closed: 'CLOSED' };
        const statusColors = { open: 'var(--red)', in_progress: 'var(--orange)', resolved: 'var(--green)', closed: 'var(--text-light)' };
        const statusBg = { open: '#fef2f2', in_progress: '#fffbeb', resolved: '#ecfdf5', closed: '#f3f4f6' };
        const statusColor = statusColors[t.status] || 'var(--text-light)';
        const statusBgColor = statusBg[t.status] || '#f3f4f6';
        return `
            <div class="help-ticket-item">
                <div class="help-ticket-head">
                    <span style="font-size:13px;font-weight:600;color:var(--text);flex:1">${escapeHtml(t.subject || 'Help Request #' + t.id)}</span>
                    <span class="help-ticket-badge" style="background:${statusBgColor};color:${statusColor};border-color:${statusColor}30">${statusLabels[t.status] || t.status.toUpperCase()}</span>
                    <span style="font-size:11px;color:var(--text-light)">${t.created_at_human}</span>
                </div>
                <p style="font-size:13px;color:var(--text-secondary);margin:6px 0 8px;">${escapeHtml(t.issue_description)}</p>
                ${t.admin_response_text ? `
                <div class="help-ticket-admin-text">
                    <strong><i class="fas fa-shield-alt"></i> Admin Reply</strong>
                    <p>${escapeHtml(t.admin_response_text)}</p>
                </div>` : `<p style="font-size:12px;color:var(--text-light);padding-top:6px;border-top:1px solid var(--border);margin-top:8px;"><i class="fas fa-clock"></i> Awaiting admin response...</p>`}
            </div>
        `;
    }).join('');
}

function settingsPageHTML() {
    return `
        <div class="page-overlay-header">
            <button class="page-overlay-back" onclick="closeOverlay()"><i class="fas fa-arrow-left"></i></button>
            <h2 class="page-overlay-title">Settings</h2>
        </div>
        <div class="card" style="max-width:600px;">
            <div class="card-title"><i class="far fa-bell" style="color:var(--primary);"></i>Notifications</div>
            <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                <div><div style="font-weight:600;font-size:14px;">Push Notifications</div><div style="font-size:12px;color:var(--text-light);">Receive alerts for messages and requests</div></div>
                <div class="toggle active" onclick="toggleEl(this)"></div>
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;">
                <div><div style="font-weight:600;font-size:14px;">Sound Effects</div><div style="font-size:12px;color:var(--text-light);">Play sounds for new messages</div></div>
                <div class="toggle active" onclick="toggleEl(this)"></div>
            </div>
        </div>
        <div class="card" style="max-width:600px;">
            <div class="card-title"><i class="fas fa-language" style="color:var(--primary);"></i>Translation</div>
            <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;">
                <div><div style="font-weight:600;font-size:14px;">Auto-Translate</div><div style="font-size:12px;color:var(--text-light);">Translate text to ASL symbols for ASL users</div></div>
                <div class="toggle active" onclick="toggleEl(this)"></div>
            </div>
        </div>
        <div class="card" style="max-width:600px;">
            <div class="card-title"><i class="fas fa-shield-alt" style="color:var(--green);"></i>Account</div>
            <div style="display:flex;flex-direction:column;gap:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;"><span style="font-size:14px;">Account Type</span><span style="font-size:13px;color:var(--text-light);">Normal User</span></div>
            </div>
        </div>
        <div class="card" style="max-width:600px;">
            <div class="card-title"><i class="fas fa-lock" style="color:var(--primary);"></i>Change Password</div>
            <div class="form-group">
                <label class="form-label">Current Password</label>
                <input type="password" class="form-input" id="settings-current-password" placeholder="Enter current password">
            </div>
            <div class="form-group">
                <label class="form-label">New Password</label>
                <input type="password" class="form-input" id="settings-new-password" placeholder="Enter new password">
            </div>
            <div class="form-group">
                <label class="form-label">Confirm New Password</label>
                <input type="password" class="form-input" id="settings-confirm-password" placeholder="Confirm new password">
            </div>
            <button class="btn btn-primary" onclick="handleChangePassword()"><i class="fas fa-key"></i> Update Password</button>
        </div>
    `;
}

function handleChangePassword() {
    const currentPassword = document.getElementById('settings-current-password').value;
    const newPassword = document.getElementById('settings-new-password').value;
    const confirmPassword = document.getElementById('settings-confirm-password').value;

    if (!currentPassword || !newPassword || !confirmPassword) {
        showToast('Please fill in all password fields.', true);
        return;
    }
    if (newPassword !== confirmPassword) {
        showToast('New passwords do not match.', true);
        return;
    }
    if (newPassword.length < 8) {
        showToast('Password must be at least 8 characters.', true);
        return;
    }

    const btn = document.querySelector('.btn-primary[onclick="handleChangePassword()"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';

    fetch('/auth/change-password/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
            confirm_password: confirmPassword,
        }),
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-key"></i> Update Password';
        if (data.success) {
            showToast('Password changed successfully!');
            document.getElementById('settings-current-password').value = '';
            document.getElementById('settings-new-password').value = '';
            document.getElementById('settings-confirm-password').value = '';
        } else {
            showToast(data.error || 'Failed to change password', true);
        }
    })
    .catch(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-key"></i> Update Password';
        showToast('Network error', true);
    });
}

function profilePageHTML() {
    const picUrl = currentUserData.profile_pic;
    const initial = (currentUserData.name || 'n').charAt(0).toUpperCase();
    return `
        <div class="page-overlay-header">
            <button class="page-overlay-back" onclick="closeOverlay()"><i class="fas fa-arrow-left"></i></button>
            <h2 class="page-overlay-title">My Profile</h2>
        </div>
        <div class="card" style="max-width:600px;">
            <div style="text-align:center;padding:24px 32px 16px;">
                <div class="profile-pic-wrap" style="position:relative;width:100px;height:100px;margin:0 auto 12px;cursor:pointer;" onclick="document.getElementById('profile-pic-input').click()">
                    ${picUrl
                        ? `<img src="${picUrl}" class="profile-pic-img" style="width:100px;height:100px;border-radius:50%;object-fit:cover;border:3px solid var(--primary);">`
                        : `<div style="width:100px;height:100px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--primary-light));display:flex;align-items:center;justify-content:center;color:#fff;font-size:38px;font-weight:600;border:3px solid var(--primary);">${initial}</div>`
                    }
                    <div style="position:absolute;bottom:0;right:0;width:32px;height:32px;border-radius:50%;background:var(--primary);color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;border:2px solid #fff;">
                        <i class="fas fa-camera"></i>
                    </div>
                </div>
                <input type="file" id="profile-pic-input" accept="image/*" style="display:none" onchange="previewProfilePic(this)">
                <div style="font-size:20px;font-weight:700;" id="profile-name-display">${escapeHtml(currentUserData.name || 'User')}</div>
                <div style="font-size:13px;color:var(--text-light);">Normal User</div>
            </div>
            <div style="padding:0 24px 24px;">
                <div id="profile-pic-preview" style="display:none;text-align:center;margin-bottom:12px;">
                    <img id="profile-pic-preview-img" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:3px solid var(--green);">
                    <p style="font-size:12px;color:var(--green);margin-top:4px;">New picture selected — save to apply</p>
                </div>
                <div class="form-group">
                    <label class="form-label">Full Name</label>
                    <input type="text" class="form-input" id="profile-full-name" value="${escapeHtml(currentUserData.name || '')}">
                </div>
                <div class="form-group">
                    <label class="form-label">Username</label>
                    <input type="text" class="form-input" id="profile-username" value="${escapeHtml(currentUserData.username || '')}">
                </div>
                <div class="form-group">
                    <label class="form-label">Email</label>
                    <input type="email" class="form-input" id="profile-email" value="${escapeHtml(currentUserData.email || '')}">
                </div>
                <button class="btn btn-primary" onclick="handleUpdateProfile()" style="width:100%;">
                    <i class="fas fa-save"></i> Save Profile
                </button>
            </div>
        </div>
    `;
}

function previewProfilePic(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('profile-pic-preview');
        const img = document.getElementById('profile-pic-preview-img');
        img.src = e.target.result;
        preview.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function handleUpdateProfile() {
    const fullName = document.getElementById('profile-full-name').value.trim();
    const username = document.getElementById('profile-username').value.trim();
    const email = document.getElementById('profile-email').value.trim();
    const picInput = document.getElementById('profile-pic-input');
    const file = picInput.files[0];

    if (!fullName || !username || !email) {
        showToast('Please fill in all fields.', true);
        return;
    }

    const btn = document.querySelector('.btn-primary[onclick="handleUpdateProfile()"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    const formData = new FormData();
    formData.append('full_name', fullName);
    formData.append('username', username);
    formData.append('email', email);
    if (file) {
        formData.append('profile_picture', file);
    }

    fetch('/auth/update-profile/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() },
        body: formData,
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Save Profile';
        if (data.success) {
            showToast('Profile updated!');
            currentUserData.name = fullName;
            currentUserData.username = username;
            currentUserData.email = email;
            if (data.user.profile_picture_url) {
                currentUserData.profile_pic = data.user.profile_picture_url;
            }
            const display = document.getElementById('profile-name-display');
            if (display) display.textContent = fullName;
            document.getElementById('profile-pic-preview').style.display = 'none';
            document.getElementById('profile-pic-input').value = '';
        } else {
            showToast(data.error || 'Failed to update profile', true);
        }
    })
    .catch(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Save Profile';
        showToast('Network error', true);
    });
}

function quickOpenChat(friendId) {
    closeOverlay();
    openConversation(friendId);
}

function showEmojiPicker() {
    showToast('Emoji picker coming soon');
}
function showAttachment() {
    showToast('File attachment coming soon');
}
function showChatMenu() {
    showToast('Chat options coming soon');
}

function signOut() {
    if (confirm('Are you sure you want to sign out?')) {
        window.location.href = '/auth/logout/';
    }
}

function toggleEl(el) { el.classList.toggle('active'); }

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
        c = c.trim();
        if (c.startsWith(name + '=')) return decodeURIComponent(c.substring(name.length + 1));
    }
    return '';
}

function showToast(message, isError) {
    const toast = document.getElementById('toast');
    const msgEl = document.getElementById('toastMessage');
    if (!toast || !msgEl) return;
    msgEl.textContent = message;
    toast.className = 'toast show' + (isError ? ' error' : '');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('show'), 3000);
}
