// Этот скрипт выполняется в контексте браузера для сбора интерактивных элементов.
// Он присваивает каждому элементу уникальный bid (browser ID) и возвращает
// упрощенное текстовое представление страницы.
(() => {
    let bidCounter = 0;
    const elements = Array.from(document.querySelectorAll(
        'a, button, input, textarea, select, [role="button"], [role="link"], h1, h2, h3'
    ));

    const simplified_elements = elements.map(el => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        // Игнорируем невидимые или пустые элементы
        if (rect.width === 0 || rect.height === 0 || style.display === 'none' || style.visibility === 'hidden') {
            return null;
        }

        const tag = el.tagName.toLowerCase();
        el.setAttribute('bid', bidCounter);

        let elementType = tag;
        let label = (el.getAttribute('aria-label') || el.placeholder || "").trim();
        let text = (el.innerText || el.value || "").trim();

        // --- Определение типа элемента ---
        if (tag === 'input') {
            const type = el.type.toLowerCase() || 'text';
            if (['text', 'search', 'email', 'password', 'url', 'tel'].includes(type)) {
                elementType = 'TextInput';
            } else if (type === 'submit' || type === 'button') {
                elementType = 'Button';
            } else if (['checkbox', 'radio'].includes(type)) {
                elementType = type.charAt(0).toUpperCase() + type.slice(1);
            } else {
                elementType = 'Input'; // Общий тип для остальных
            }
        } else if (tag === 'textarea') {
            elementType = 'TextArea';
        } else if (tag === 'a' || el.getAttribute('role') === 'link') {
            elementType = 'Link';
        } else if (tag === 'button' || el.getAttribute('role') === 'button') {
            elementType = 'Button';
        } else if (tag.startsWith('h')) {
            // Форматируем заголовки для лучшей читаемости
            const headerText = `\n--- ${text} ---`;
            bidCounter++;
            return headerText;
        }

        // Пытаемся найти связанный <label> по атрибуту 'for'
        if (!label && el.id) {
            const labelEl = document.querySelector(`label[for='${el.id}']`);
            if (labelEl) label = labelEl.innerText.trim();
        }

        // Формируем финальную строку, ограничивая длину метки
        const effectiveLabel = (label || text).substring(0, 100);
        const line = `[${elementType} bid=${bidCounter}, label="${effectiveLabel}"]`;

        bidCounter++;
        return line;
    }).filter(Boolean); // Убираем null элементы

    return `[URL] ${window.location.href}\n[Title] ${document.title}\n\n` + simplified_elements.join('\n');
})();