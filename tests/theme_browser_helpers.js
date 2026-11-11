// Test-only observation at the canvas consumption boundary; retain native drawing.
window.themeDraws = [];
window.themeRendered = [];
document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart !== 'undefined') Chart.register({
        id: 'theme-test-render-complete',
        afterRender(chart) { window.themeRendered.push(chart.canvas.id); }
    });
});
const nativeFillText = CanvasRenderingContext2D.prototype.fillText;
CanvasRenderingContext2D.prototype.fillText = function(text, ...args) {
    const result = nativeFillText.call(this, text, ...args);
    window.themeDraws.push({canvas: this.canvas.id, text: String(text), color: this.fillStyle});
    return result;
};

window.textContrast = element => {
    const rgba = value => {
        const values = value.match(/[\d.]+/g).map(Number);
        if (!value.startsWith('rgb')) throw new Error('Unsupported color: ' + value);
        return [...values.slice(0, 3), values[3] ?? 1];
    };
    const over = (front, back) => {
        const alpha = front[3] + back[3] * (1 - front[3]);
        return [...front.slice(0, 3).map((v, i) =>
            (v * front[3] + back[i] * back[3] * (1 - front[3])) / alpha), alpha];
    };
    const backgrounds = node => {
        if (!node) return [[255, 255, 255, 1]];
        const style = getComputedStyle(node);
        if (Number(style.opacity) !== 1) throw new Error('Opacity needs explicit compositing');
        let layers = [rgba(style.backgroundColor)];
        if (style.backgroundImage !== 'none') {
            // This template only uses opaque, two-stop linear header gradients.
            // Check both rendered endpoint colors, including metadata overlays.
            if (!style.backgroundImage.startsWith('linear-gradient('))
                throw new Error('Unsupported background: ' + style.backgroundImage);
            layers = style.backgroundImage.match(/rgba?\([^)]+\)/g).map(rgba);
            if (layers.some(color => color[3] !== 1))
                throw new Error('Transparent gradient needs explicit compositing');
        }
        return backgrounds(node.parentElement).flatMap(back => layers.map(front => over(front, back)));
    };
    const luminance = color => {
        const rgb = color.slice(0, 3).map(v => v / 255)
            .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
        return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
    };
    const style = getComputedStyle(element);
    const foreground = rgba(style.color);
    const samples = backgrounds(element).map(background => {
        const a = luminance(over(foreground, background)), b = luminance(background);
        return {background, ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05)};
    });
    return {color: style.color, samples, ratio: Math.min(...samples.map(s => s.ratio))};
};
