import re

with open('negocio/views.py', 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Fix hub_view nested trys
    if 'try:' in line and 'if user.empresa:' in lines[i+1] if i+1 < len(lines) else False:
        # We are at line 45
        replacement = """    empresas = Empresa.objects.filter(usuario=user).all()
    vendedores = Vendedor.objects.filter(usuario=user).all()
    tenderos = Tendero.objects.filter(usuario=user).all()

    if len(empresas) > 0:
        tipo_usuario = 'Empresa'
        nombre_usuario = empresas[0].razon_social
        plantilla = 'hub_empresa.html'
    elif len(vendedores) > 0:
        tipo_usuario = 'Vendedor'
        nombre_usuario = f"{user.first_name} {user.last_name}"
        plantilla = 'hub_vendedor.html'
    elif len(tenderos) > 0:
        tipo_usuario = 'Tendero'
        nombre_usuario = f"{user.first_name} {user.last_name}"
        plantilla = 'hub_tendero.html'
"""
        new_lines.append(replacement)
        # skip until 'pass # Se queda con los valores'
        while i < len(lines) and 'pass # Se queda con los valores' not in lines[i]:
            i += 1
        i += 1 # skip the pass line too
        continue

    # Fix other standard trys
    match_empresa = re.search(r'^(\s*)try:\s*$', line)
    if match_empresa:
        # Check next line
        next_line = lines[i+1] if i+1 < len(lines) else ""
        if "mi_empresa = request.user.empresa" in next_line:
            indent = match_empresa.group(1)
            new_lines.append(f"{indent}mis_empresas = Empresa.objects.filter(usuario=request.user).all()\n")
            new_lines.append(f"{indent}if len(mis_empresas) > 0:\n")
            new_lines.append(f"{indent}    mi_empresa = mis_empresas[0]\n")
            i += 2
            continue
        elif "mi_vendedor = request.user.vendedor" in next_line:
            indent = match_empresa.group(1)
            new_lines.append(f"{indent}mis_vendedores = Vendedor.objects.filter(usuario=request.user).all()\n")
            new_lines.append(f"{indent}if len(mis_vendedores) > 0:\n")
            new_lines.append(f"{indent}    mi_vendedor = mis_vendedores[0]\n")
            i += 2
            continue
        elif "mi_tendero = request.user.tendero" in next_line:
            indent = match_empresa.group(1)
            new_lines.append(f"{indent}mis_tenderos = Tendero.objects.filter(usuario=request.user).all()\n")
            new_lines.append(f"{indent}if len(mis_tenderos) > 0:\n")
            new_lines.append(f"{indent}    mi_tendero = mis_tenderos[0]\n")
            i += 2
            continue
    
    # Fix except blocks
    match_except = re.search(r'^(\s*)except.*DoesNotExist.*:\s*$', line)
    if match_except:
        indent = match_except.group(1)
        new_lines.append(f"{indent}else:\n")
        i += 1
        continue
    match_except2 = re.search(r'^(\s*)except Exception as e:\s*$', line)
    if match_except2:
        indent = match_except2.group(1)
        new_lines.append(f"{indent}else:\n")
        i += 1
        continue

    new_lines.append(line)
    i += 1

with open('negocio/views.py', 'w') as f:
    f.writelines(new_lines)
