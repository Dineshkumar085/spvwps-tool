import cairosvg

svg_code = open('icon.svg', 'r').read()

cairosvg.svg2png(url='icon.svg', write_to='static/icon-192.png', output_width=192, output_height=192)
cairosvg.svg2png(url='icon.svg', write_to='static/icon-512.png', output_width=512, output_height=512)
cairosvg.svg2png(url='icon.svg', write_to='static/favicon.ico', output_width=32, output_height=32)
print('Done!')