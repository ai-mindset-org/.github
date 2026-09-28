# .github

Профиль организации `ai-mindset-org`. GitHub показывает `profile/README.md` на странице
https://github.com/ai-mindset-org — этот файл, который вы читаете, виден только здесь, в репозитории.

```
profile/README.md          витрина организации (английский, тексты — перевод с aimindset.org)
profile/banner-dark.svg    баннер 1200×400 для тёмной темы
profile/banner-light.svg   то же для светлой
tools/banner/              генератор обоих баннеров, кубики из Blender-модели, шрифты
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

Знак AIM собран из 853 кубиков воксельной модели `voxel_object.blend` (Blender), вид строго
спереди: слева кубики плотные, справа меньше, с заметной сеткой, как в модели. Глаза и разрез —
сквозные отверстия. При открытии страницы каждый кубик прилетает из облака вокруг знака
с поворотом и встаёт на место, сначала левая половина, затем правая. Сборка около 4 секунд,
один раз, без цикла.

Движение на SMIL (`animate` + `animateTransform`, `fill="freeze"`): GitHub вырезает из SVG
`<script>`, а CSS-анимации через camo работают ненадёжно. Текст переведён в кривые
(IBM Plex Mono, заголовок Space Grotesk 700), шрифты на GitHub не грузятся.

Пересобрать после правки текста или палитры:

```bash
cd tools/banner && python make_banner.py
```

Пишет сразу в `profile/`. Нужны `pip install fonttools brotli`.

Если поменялась модель в Blender — сначала обновить координаты:

```bash
blender -b voxel_object.blend --python tools/banner/extract_cubes.py
```

Правится в `tools/banner/make_banner.py`: `THEME` — палитры светлой и тёмной темы,
`logo()` — разлёт и задержки кубиков, `u` в `banner()` — размер кубика, блок `text(...)` — строки.
