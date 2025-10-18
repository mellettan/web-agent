(() => {
    const MAX_TEXT = 80;
    const MAX_OPTIONS = 10;
    const SELECTOR = [
        'a[href]', 'button', 'input:not([type="hidden"])', 'textarea', 'select', 'summary',
        '[role="button"]', '[role="link"]', '[role="tab"]', '[role="menuitem"]', '[role="checkbox"]',
        '[contenteditable="true"]', 'h1', 'h2', 'h3',
    ].join(', ');

    const clean = (value) => (value || '').replace(/\s+/g, ' ').replace(/"/g, "'").trim().slice(0, MAX_TEXT);

    const isVisible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden'
            && style.display !== 'none' && style.opacity !== '0';
    };

    const labelOf = (el) => {
        const direct = el.getAttribute('aria-label') || el.getAttribute('title');
        if (direct) return direct;
        const labelledBy = el.getAttribute('aria-labelledby');
        const reference = labelledBy && document.getElementById(labelledBy);
        if (reference) return reference.innerText;
        if (el.id) {
            const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
            if (label) return label.innerText;
        }
        const wrapping = el.closest('label');
        if (wrapping) return wrapping.innerText;
        return el.placeholder || el.innerText || el.value || el.getAttribute('alt') || '';
    };

    const kindOf = (el) => {
        const tag = el.tagName.toLowerCase();
        const role = el.getAttribute('role');
        if (tag === 'input') {
            const type = (el.type || 'text').toLowerCase();
            if (['submit', 'button', 'reset', 'image'].includes(type)) return 'Button';
            if (type === 'checkbox') return 'Checkbox';
            if (type === 'radio') return 'Radio';
            return 'TextInput';
        }
        if (tag === 'textarea' || el.isContentEditable) return 'TextArea';
        if (tag === 'select') return 'Select';
        if (tag === 'a' || role === 'link') return 'Link';
        if (role === 'checkbox') return 'Checkbox';
        if (role === 'tab') return 'Tab';
        if (role === 'menuitem') return 'MenuItem';
        return 'Button';
    };

    document.querySelectorAll('[data-bid]').forEach((el) => el.removeAttribute('data-bid'));

    const lines = [`[URL] ${location.href}`, `[Title] ${document.title}`];
    let bid = 0;
    for (const el of document.querySelectorAll(SELECTOR)) {
        if (!isVisible(el)) continue;
        const tag = el.tagName.toLowerCase();
        if (/^h[1-3]$/.test(tag)) {
            const heading = clean(el.innerText);
            if (heading) lines.push('', `## ${heading}`);
            continue;
        }
        el.setAttribute('data-bid', String(bid));
        const attributes = [`bid=${bid}`, `label="${clean(labelOf(el))}"`];
        if (el.disabled) attributes.push('disabled');
        if (el.type === 'checkbox' || el.type === 'radio') attributes.push(el.checked ? 'checked' : 'unchecked');
        if (tag === 'select') {
            const options = Array.from(el.options).slice(0, MAX_OPTIONS).map((option) => clean(option.text));
            attributes.push(`options="${options.join(' | ')}"`);
        }
        const isTextField = tag === 'textarea' || kindOf(el) === 'TextInput';
        if (isTextField && el.value && el.type !== 'password') {
            attributes.push(`value="${clean(el.value)}"`);
        }
        lines.push(`[${kindOf(el)} ${attributes.join(', ')}]`);
        bid += 1;
    }
    return lines.join('\n');
})()
