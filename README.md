# .github

Профиль организации `ai-mindset-org`. GitHub показывает `profile/README.md` на странице
https://github.com/ai-mindset-org — этот файл, который вы читаете, виден только здесь, в репозитории.

```
profile/README.md          витрина организации (английский, тексты — перевод с aimindset.org)
profile/banner-dark.svg    баннер 1200×400 для тёмной темы
profile/banner-light.svg   то же для светлой
tools/make_banner.py       генератор обоих баннеров
tools/make_avatar.py       генератор аватаров организации
tools/logo.png             знак AIM, из которого собираются точки
tools/avatar/              аватары 500×500 и лист с превью
```

## Аватар

Аватар организации меняется только вручную и только владельцем орги:
https://github.com/organizations/ai-mindset-org/settings/profile → Upload new picture.
API для смены аватара организации у GitHub нет.

`tools/avatar/avatar-dark.png` — основной, белый знак на чёрном поле. Рядом бумажный
и точечный варианты, `preview.png` показывает все три в 260, 96 и 40 пикселей.
Пересобрать: `cd tools && python make_avatar.py`.

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
