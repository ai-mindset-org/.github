# .github

Профиль организации `ai-mindset-org`. GitHub показывает `profile/README.md` на странице
https://github.com/ai-mindset-org — этот файл, который вы читаете, виден только здесь, в репозитории.

```
profile/README.md          витрина организации (английский, тексты — перевод с aimindset.org)
profile/banner-dark.svg    баннер 1200×400 для тёмной темы
profile/banner-light.svg   то же для светлой
tools/make_banner.py       генератор обоих баннеров
tools/logo.png             знак AIM, из которого собираются точки
```

## Баннер

Анимация — разлёт правой половины знака, как в hero на aimindset.org. Знак дискретизируется
по альфа-каналу `logo.png` в точки: левая половина держит форму, правые точки уходят наружу
по своим векторам и возвращаются. Цикл 6 секунд, замкнутый.

Движение запечено в SMIL (`animateTransform` с тремя ключами на точку): GitHub вырезает из SVG
`<script>`, а CSS-анимации через camo работают ненадёжно, поэтому анимация только декларативная.

Шрифт — системный моно (`ui-monospace`, `SF Mono`, `Consolas`), внешние шрифты в SVG на GitHub
не загружаются.

Пересобрать после правки текста или параметров:

```bash
cd tools && python make_banner.py
cp banner-*.svg ../profile/
```

Нужен Pillow: `pip install pillow`.

Правится в `tools/make_banner.py`: `THEMES` — палитры, `MARK_CX/MARK_CY/MARK_SIZE` — положение
и размер знака, `STEP` — плотность точек, `SCATTER` — амплитуда разлёта, блок «текст» — строки
баннера.
