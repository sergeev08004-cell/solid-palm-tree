"use strict";

const GRID_SIZE = 10;
const LETTERS = ["А", "Б", "В", "Г", "Д", "Е", "Ж", "З", "И", "К"];
const SHIP_LENGTHS = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1];
const CARDINAL_DIRECTIONS = [
  { x: 1, y: 0 },
  { x: -1, y: 0 },
  { x: 0, y: 1 },
  { x: 0, y: -1 }
];

const ui = {
  newGameButton: document.querySelector("#new-game"),
  status: document.querySelector("#status"),
  playerBoard: document.querySelector("#player-board"),
  enemyBoard: document.querySelector("#enemy-board"),
  playerSummary: document.querySelector("#player-summary"),
  enemySummary: document.querySelector("#enemy-summary")
};

const view = {
  playerCells: [],
  enemyCells: []
};

let game = null;

initialize();

function initialize() {
  hydrateAxes();
  buildBoards();
  ui.newGameButton.addEventListener("click", startNewGame);
  startNewGame();
}

function hydrateAxes() {
  document.querySelectorAll(".axis-top").forEach((axis) => {
    axis.replaceChildren();
    LETTERS.forEach((letter) => {
      const span = document.createElement("span");
      span.textContent = letter;
      axis.append(span);
    });
  });

  document.querySelectorAll(".axis-side").forEach((axis) => {
    axis.replaceChildren();
    for (let index = 1; index <= GRID_SIZE; index += 1) {
      const span = document.createElement("span");
      span.textContent = String(index);
      axis.append(span);
    }
  });
}

function buildBoards() {
  view.playerCells = buildBoard(ui.playerBoard, "player");
  view.enemyCells = buildBoard(ui.enemyBoard, "enemy");
}

function buildBoard(container, owner) {
  const rows = [];
  container.replaceChildren();

  for (let y = 0; y < GRID_SIZE; y += 1) {
    const row = [];

    for (let x = 0; x < GRID_SIZE; x += 1) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      cell.dataset.x = String(x);
      cell.dataset.y = String(y);
      cell.style.setProperty("--tilt", `${noise(x, y, owner, 1) * 3.6 - 1.8}deg`);
      cell.style.setProperty("--drift-x", `${noise(x, y, owner, 2) * 2.4 - 1.2}px`);
      cell.style.setProperty("--drift-y", `${noise(x, y, owner, 3) * 2.4 - 1.2}px`);
      cell.style.setProperty("--delay", `${Math.round(noise(x, y, owner, 4) * 240)}ms`);

      if (owner === "enemy") {
        cell.addEventListener("click", () => handlePlayerShot(x, y));
      } else {
        cell.tabIndex = -1;
      }

      container.append(cell);
      row.push(cell);
    }

    rows.push(row);
  }

  return rows;
}

function startNewGame() {
  if (game?.pendingAiTurn) {
    window.clearTimeout(game.pendingAiTurn);
  }

  const playerField = createField();
  const enemyField = createField();

  placeFleetRandomly(playerField);
  placeFleetRandomly(enemyField);

  game = {
    playerField,
    enemyField,
    turn: "player",
    over: false,
    pendingAiTurn: null,
    ai: createAiBrain()
  };

  setStatus("Ваш ход. Начинайте обстрел по правому полю.", "neutral");
  render();
}

function createField() {
  return {
    grid: Array.from({ length: GRID_SIZE }, () =>
      Array.from({ length: GRID_SIZE }, () => ({
        shipId: null,
        shot: false,
        auto: false
      }))
    ),
    ships: []
  };
}

function createAiBrain() {
  return {
    availableShots: buildAiShotPool(),
    targetHits: [],
    targetQueue: []
  };
}

function buildAiShotPool() {
  const primary = [];
  const secondary = [];

  for (let y = 0; y < GRID_SIZE; y += 1) {
    for (let x = 0; x < GRID_SIZE; x += 1) {
      const target = { x, y };
      if ((x + y) % 2 === 0) {
        primary.push(target);
      } else {
        secondary.push(target);
      }
    }
  }

  shuffle(primary);
  shuffle(secondary);
  return primary.concat(secondary);
}

function placeFleetRandomly(field) {
  SHIP_LENGTHS.forEach((length) => {
    const shipId = field.ships.length;
    const ship = {
      id: shipId,
      length,
      title: shipTitle(length),
      cells: [],
      hits: 0,
      sunk: false
    };

    let placed = false;
    let attempts = 0;

    while (!placed && attempts < 5000) {
      attempts += 1;
      const horizontal = Math.random() > 0.5;
      const startX = randomInt(0, horizontal ? GRID_SIZE - length : GRID_SIZE - 1);
      const startY = randomInt(0, horizontal ? GRID_SIZE - 1 : GRID_SIZE - length);

      if (!canPlaceShip(field, startX, startY, length, horizontal)) {
        continue;
      }

      for (let offset = 0; offset < length; offset += 1) {
        const x = startX + (horizontal ? offset : 0);
        const y = startY + (horizontal ? 0 : offset);
        field.grid[y][x].shipId = shipId;
        ship.cells.push({ x, y });
      }

      field.ships.push(ship);
      placed = true;
    }

    if (!placed) {
      throw new Error("Не удалось расставить флот.");
    }
  });
}

function canPlaceShip(field, startX, startY, length, horizontal) {
  for (let offset = 0; offset < length; offset += 1) {
    const x = startX + (horizontal ? offset : 0);
    const y = startY + (horizontal ? 0 : offset);

    if (!isInsideBoard(x, y) || field.grid[y][x].shipId !== null) {
      return false;
    }

    for (let dy = -1; dy <= 1; dy += 1) {
      for (let dx = -1; dx <= 1; dx += 1) {
        const neighborX = x + dx;
        const neighborY = y + dy;

        if (!isInsideBoard(neighborX, neighborY)) {
          continue;
        }

        if (field.grid[neighborY][neighborX].shipId !== null) {
          return false;
        }
      }
    }
  }

  return true;
}

function handlePlayerShot(x, y) {
  if (!game || game.over || game.turn !== "player") {
    return;
  }

  const result = fireAt(game.enemyField, x, y);
  if (!result.valid) {
    return;
  }

  if (result.hit) {
    if (isFleetDestroyed(game.enemyField)) {
      setStatus("Победа! Весь вражеский флот заштрихован попаданиями.", "success");
      game.over = true;
      render();
      return;
    }

    const note = result.sunk
      ? `Попадание! Вы потопили вражеский ${result.ship.title} и можете стрелять еще.`
      : "Попадание! Продолжайте атаку, ход остается за вами.";
    setStatus(note, "success");
    render();
    return;
  }

  game.turn = "enemy";
  setStatus(`Мимо по ${formatCoordinate(x, y)}. Компьютер готовит ответный ход.`, "warning");
  render();
  scheduleAiTurn();
}

function scheduleAiTurn() {
  if (!game || game.over) {
    return;
  }

  if (game.pendingAiTurn) {
    window.clearTimeout(game.pendingAiTurn);
  }

  game.pendingAiTurn = window.setTimeout(runAiTurn, 720);
}

function runAiTurn() {
  if (!game || game.over || game.turn !== "enemy") {
    return;
  }

  game.pendingAiTurn = null;

  const shot = chooseAiShot();
  if (!shot) {
    return;
  }

  const result = fireAt(game.playerField, shot.x, shot.y);
  if (!result.valid) {
    runAiTurn();
    return;
  }

  if (result.hit) {
    rememberAiHit(shot, result.sunk);

    if (isFleetDestroyed(game.playerField)) {
      game.over = true;
      setStatus(
        `Компьютер попал по ${formatCoordinate(shot.x, shot.y)} и добил ваш последний корабль. Реванш?`,
        "danger"
      );
      render();
      return;
    }

    const note = result.sunk
      ? `Компьютер попал по ${formatCoordinate(shot.x, shot.y)} и потопил ваш ${result.ship.title}.`
      : `Компьютер попал по ${formatCoordinate(shot.x, shot.y)} и продолжает добивание.`;
    setStatus(note, result.sunk ? "danger" : "warning");
    render();
    scheduleAiTurn();
    return;
  }

  game.turn = "player";
  setStatus(`Компьютер промахнулся по ${formatCoordinate(shot.x, shot.y)}. Теперь ваш ход.`, "neutral");
  render();
}

function chooseAiShot() {
  while (game.ai.targetQueue.length > 0) {
    const queued = game.ai.targetQueue.shift();
    if (!game.playerField.grid[queued.y][queued.x].shot) {
      return queued;
    }
  }

  while (game.ai.availableShots.length > 0) {
    const candidate = game.ai.availableShots.shift();
    if (!game.playerField.grid[candidate.y][candidate.x].shot) {
      return candidate;
    }
  }

  return null;
}

function rememberAiHit(shot, sunk) {
  if (sunk) {
    game.ai.targetHits = [];
    game.ai.targetQueue = [];
    return;
  }

  if (!game.ai.targetHits.some((cell) => cell.x === shot.x && cell.y === shot.y)) {
    game.ai.targetHits.push(shot);
  }

  game.ai.targetQueue = buildTargetQueue(game.ai.targetHits, game.playerField);
}

function buildTargetQueue(hits, field) {
  if (hits.length === 0) {
    return [];
  }

  if (hits.length === 1) {
    return shuffle(
      CARDINAL_DIRECTIONS
        .map((direction) => ({
          x: hits[0].x + direction.x,
          y: hits[0].y + direction.y
        }))
        .filter((cell) => isAvailableTarget(cell, field))
    );
  }

  const first = hits[0];
  const sameRow = hits.every((cell) => cell.y === first.y);
  const sameColumn = hits.every((cell) => cell.x === first.x);

  if (sameRow) {
    const y = first.y;
    const xs = hits.map((cell) => cell.x).sort((left, right) => left - right);
    return [
      { x: xs[0] - 1, y },
      { x: xs[xs.length - 1] + 1, y }
    ].filter((cell) => isAvailableTarget(cell, field));
  }

  if (sameColumn) {
    const x = first.x;
    const ys = hits.map((cell) => cell.y).sort((top, bottom) => top - bottom);
    return [
      { x, y: ys[0] - 1 },
      { x, y: ys[ys.length - 1] + 1 }
    ].filter((cell) => isAvailableTarget(cell, field));
  }

  return shuffle(
    hits
      .flatMap((hit) =>
        CARDINAL_DIRECTIONS.map((direction) => ({
          x: hit.x + direction.x,
          y: hit.y + direction.y
        }))
      )
      .filter((cell, index, list) => {
        const isUnique = list.findIndex((item) => item.x === cell.x && item.y === cell.y) === index;
        return isUnique && isAvailableTarget(cell, field);
      })
  );
}

function isAvailableTarget(cell, field) {
  return isInsideBoard(cell.x, cell.y) && !field.grid[cell.y][cell.x].shot;
}

function fireAt(field, x, y) {
  const cell = field.grid[y][x];
  if (cell.shot) {
    return { valid: false };
  }

  cell.shot = true;
  cell.auto = false;

  if (cell.shipId === null) {
    return { valid: true, hit: false };
  }

  const ship = field.ships[cell.shipId];
  ship.hits += 1;

  if (ship.hits === ship.length) {
    ship.sunk = true;
    surroundSunkShip(field, ship);
    return { valid: true, hit: true, sunk: true, ship };
  }

  return { valid: true, hit: true, sunk: false, ship };
}

function surroundSunkShip(field, ship) {
  ship.cells.forEach((segment) => {
    for (let dy = -1; dy <= 1; dy += 1) {
      for (let dx = -1; dx <= 1; dx += 1) {
        const x = segment.x + dx;
        const y = segment.y + dy;

        if (!isInsideBoard(x, y)) {
          continue;
        }

        const cell = field.grid[y][x];
        if (cell.shipId === null && !cell.shot) {
          cell.shot = true;
          cell.auto = true;
        }
      }
    }
  });
}

function isFleetDestroyed(field) {
  return field.ships.every((ship) => ship.sunk);
}

function setStatus(message, tone) {
  ui.status.textContent = message;
  ui.status.className = `status-text tone-${tone}`;
}

function render() {
  renderField(game.playerField, view.playerCells, true, false);
  renderField(game.enemyField, view.enemyCells, false, game.turn === "player" && !game.over);
  renderSummary(game.playerField, ui.playerSummary, true);
  renderSummary(game.enemyField, ui.enemySummary, false);
}

function renderField(field, cellRefs, revealShips, interactive) {
  for (let y = 0; y < GRID_SIZE; y += 1) {
    for (let x = 0; x < GRID_SIZE; x += 1) {
      const state = field.grid[y][x];
      const ship = state.shipId === null ? null : field.ships[state.shipId];
      const cell = cellRefs[y][x];

      cell.className = "cell";
      cell.disabled = !interactive || state.shot;

      if (interactive && !state.shot) {
        cell.classList.add("targetable");
      }

      if (revealShips && state.shipId !== null) {
        cell.classList.add("ship");
      }

      if (state.shot && state.shipId === null) {
        cell.classList.add("miss");
        if (state.auto) {
          cell.classList.add("auto-mark");
        }
      }

      if (state.shot && state.shipId !== null) {
        cell.classList.add("hit");
      }

      if (ship?.sunk) {
        cell.classList.add("sunk");
      }

      cell.setAttribute("aria-label", describeCell(revealShips, state, ship, x, y));
      cell.title = describeCell(revealShips, state, ship, x, y);
    }
  }
}

function renderSummary(field, target, isPlayer) {
  const afloat = field.ships.filter((ship) => !ship.sunk).length;
  const hits = field.ships.reduce((total, ship) => total + ship.hits, 0);

  target.textContent = isPlayer
    ? `На плаву: ${afloat} из ${field.ships.length}. Пробоин получено: ${hits}.`
    : `Не потоплено: ${afloat} из ${field.ships.length}. Ваших попаданий: ${hits}.`;
}

function describeCell(revealShips, state, ship, x, y) {
  const prefix = formatCoordinate(x, y);

  if (state.shot && state.shipId !== null && ship?.sunk) {
    return `${prefix}: потопленный корабль`;
  }

  if (state.shot && state.shipId !== null) {
    return `${prefix}: попадание`;
  }

  if (state.shot) {
    return `${prefix}: промах`;
  }

  if (revealShips && state.shipId !== null) {
    return `${prefix}: ваш корабль`;
  }

  return `${prefix}: неизвестная клетка`;
}

function shipTitle(length) {
  if (length === 4) {
    return "линкор";
  }

  if (length === 3) {
    return "крейсер";
  }

  if (length === 2) {
    return "эсминец";
  }

  return "катер";
}

function formatCoordinate(x, y) {
  return `${LETTERS[x]}${y + 1}`;
}

function isInsideBoard(x, y) {
  return x >= 0 && x < GRID_SIZE && y >= 0 && y < GRID_SIZE;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function shuffle(items) {
  for (let index = items.length - 1; index > 0; index -= 1) {
    const swapIndex = randomInt(0, index);
    [items[index], items[swapIndex]] = [items[swapIndex], items[index]];
  }

  return items;
}

function noise(x, y, owner, seed) {
  const ownerSalt = owner === "player" ? 17.31 : 43.73;
  const raw = Math.sin((x + 1) * 12.9898 + (y + 1) * 78.233 + seed * 37.719 + ownerSalt) * 43758.5453;
  return raw - Math.floor(raw);
}
