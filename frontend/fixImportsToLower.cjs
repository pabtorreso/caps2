const fs = require("fs");
const path = require("path");

function walk(dir, filelist = []) {
  const files = fs.readdirSync(dir);
  files.forEach(file => {
    const filepath = path.join(dir, file);
    const stat = fs.statSync(filepath);
    if (stat.isDirectory()) {
      walk(filepath, filelist);
    } else if (/\.(js|jsx|ts|tsx)$/.test(file)) {
      filelist.push(filepath);
    }
  });
  return filelist;
}

function fixImports(filePath) {
  let content = fs.readFileSync(filePath, "utf8");
  const regex = /from\s+["']([^"']+)["']/g;

  content = content.replace(regex, (match, importPath) => {
    if (!importPath.startsWith(".")) return match;

    const fullPath = path.resolve(path.dirname(filePath), importPath);
    const dirname = path.dirname(fullPath);
    const basename = path.basename(fullPath);
    if (!fs.existsSync(dirname)) return match;

    const files = fs.readdirSync(dirname);
    const matchFile = files.find(f => f.toLowerCase() === basename.toLowerCase());

    if (matchFile && matchFile !== basename) {
      const newPath = importPath.replace(basename, matchFile.toLowerCase());
      return `from "${newPath}"`;
    }
    return match;
  });

  fs.writeFileSync(filePath, content, "utf8");
}

const baseDir = path.resolve(__dirname, "src");
const files = walk(baseDir);
files.forEach(f => fixImports(f));

console.log("✅ Imports actualizados a minúsculas.");
