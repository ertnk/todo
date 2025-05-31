let currentTaskId = null;

// タスク一覧の取得と表示
async function loadTasks() {
    try {
        const [notDoneResponse, doneResponse] = await Promise.all([
            fetch('/todos/not_done'),
            fetch('/todos/done')
        ]);

        if (!notDoneResponse.ok || !doneResponse.ok) {
            throw new Error('タスクの取得に失敗しました');
        }

        const [notDoneTasks, doneTasks] = await Promise.all([
            notDoneResponse.json(),
            doneResponse.json()
        ]);

        displayTasks(notDoneTasks, 'not-done-tasks');
        displayTasks(doneTasks, 'done-tasks');
    } catch (error) {
        console.error('タスクの取得エラー:', error);
        alert('エラーが発生しました: ' + error.message);
    }
}

// タスクの表示
function displayTasks(tasks, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = tasks.map(task => `
        <div class="task-item ${task.done ? 'done' : ''}" data-id="${task.id}">
            <div class="task-content">
                <div class="task-title">${task.title}</div>
                <div class="task-deadline">期限: ${task.deadline}</div>
                <div class="task-tags">
                    ${task.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
            </div>
            <div class="task-actions">
                <button class="toggle-status-button ${task.done ? 'uncomplete' : 'complete'}" 
                        onclick="toggleTaskStatus('${task.id}', ${!task.done})">
                    ${task.done ? '未完了にする' : '完了にする'}
                </button>
                <button class="edit-button" onclick="editTask('${task.id}')">編集</button>
                <button class="delete-button" onclick="deleteTask('${task.id}')">削除</button>
            </div>
        </div>
    `).join('');
}

// モーダルの表示
function showAddTaskModal() {
    currentTaskId = null;
    document.getElementById('modalTitle').textContent = '新規タスク';
    document.getElementById('taskForm').reset();
    document.getElementById('taskModal').style.display = 'block';
}

// タスクの編集
async function editTask(taskId) {
    try {
        const response = await fetch(`/todos/${taskId}`);
        if (!response.ok) {
            throw new Error('タスクの取得に失敗しました');
        }
        const task = await response.json();
        
        currentTaskId = taskId;
        document.getElementById('modalTitle').textContent = 'タスクの編集';
        document.getElementById('title').value = task.title;
        document.getElementById('deadline').value = task.deadline.split('T')[0];
        document.getElementById('tags').value = task.tags.join(', ');
        document.getElementById('taskModal').style.display = 'block';
    } catch (error) {
        console.error('タスクの編集エラー:', error);
        alert('エラーが発生しました: ' + error.message);
    }
}

// モーダルの閉じる
function closeModal() {
    document.getElementById('taskModal').style.display = 'none';
}

function getCurrentTimeRounded() {
    const now = new Date();
    const minutes = Math.ceil(now.getMinutes() / 15) * 15;
    now.setMinutes(minutes);
    now.setSeconds(0);
    now.setMilliseconds(0);
    return now.toISOString().slice(0, 16);  // YYYY-MM-DDTHH:mm 形式
}

// フォーム送信ハンドラ
async function handleTaskSubmit(e) {
    e.preventDefault();  // デフォルトの送信動作を防ぐ
    e.stopPropagation();  // イベントの伝播を防ぐ
    
    console.log('フォーム送信開始');

    const form = document.getElementById('taskForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    // TodoCreateモデルに合わせたデータ構造
    const taskData = {
        title: document.getElementById('title').value.trim(),
        deadline: document.getElementById('deadline').value,
        tags: document.getElementById('tags').value.split(',').map(tag => tag.trim()).filter(tag => tag),
        done: false
    };

    if (!taskData.title || !taskData.deadline) {
        alert('タイトルと期限は必須項目です。');
        return;
    }

    console.log('送信するデータ:', taskData);

    try {
        if (currentTaskId) {
            console.log('タスク更新:', currentTaskId);
            const response = await fetch(`/todos/${currentTaskId}`);
            if (!response.ok) {
                throw new Error('タスクの取得に失敗しました');
            }
            const currentTask = await response.json();
            taskData.done = currentTask.done;
            
            const updateResponse = await fetch(`/todos/${currentTaskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });
            if (!updateResponse.ok) {
                throw new Error('タスクの更新に失敗しました');
            }
            console.log('タスク更新完了');
        } else {
            console.log('新規タスク作成');
            const createResponse = await fetch('/todos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(taskData)
            });

            if (!createResponse.ok) {
                const errorData = await createResponse.json().catch(() => ({}));
                console.error('サーバーからのエラーレスポンス:', errorData);
                throw new Error(`タスクの作成に失敗しました: ${errorData.detail || createResponse.statusText}`);
            }

            const createdTask = await createResponse.json();
            console.log('新規タスク作成完了:', createdTask);
        }

        form.reset();
        closeModal();
        await loadTasks();
    } catch (error) {
        console.error('タスクの保存エラー:', error);
        alert('エラーが発生しました: ' + error.message);
    }
}

// タスクの削除
async function deleteTask(taskId) {
    if (!confirm('このタスクを削除してもよろしいですか？')) return;
    
    try {
        await fetch(`/todos/${taskId}`, { method: 'DELETE' });
        loadTasks();
    } catch (error) {
        alert('エラーが発生しました: ' + error.message);
    }
}

// タスクの状態を切り替える
async function toggleTaskStatus(taskId, newStatus) {
    try {
        const response = await fetch(`/todos/${taskId}`);
        if (!response.ok) {
            throw new Error('タスクの取得に失敗しました');
        }
        const currentTask = await response.json();
        
        const taskData = {
            title: currentTask.title,
            deadline: currentTask.deadline,
            tags: currentTask.tags,
            done: newStatus
        };

        const updateResponse = await fetch(`/todos/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(taskData)
        });

        if (!updateResponse.ok) {
            throw new Error('タスクの状態更新に失敗しました');
        }

        await loadTasks();
    } catch (error) {
        console.error('タスクの状態更新エラー:', error);
        alert('エラーが発生しました: ' + error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('showAddTaskBtn').addEventListener('click', showAddTaskModal);
    document.getElementById('closeModalBtn').addEventListener('click', closeModal);
    document.getElementById('taskForm').addEventListener('submit', handleTaskSubmit);
    // 初期タスク読み込み
    loadTasks();
});