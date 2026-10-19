import { getLineStation, getMetroLinePaths, metroLineById, metroLines, metroStationById, metroStations, metroTransferGroups, sameNameTransferExclusions, stationNodeId, } from "../data/metroData.js";
export const METRO_MAP_STYLE = {
    lineWidth: 5,
    routeLineWidth: 7,
    routeHaloWidth: 11,
    stationRadius: 4,
    transferRadius: 7,
    lineOpacity: 0.82,
    inactiveLineOpacity: 0.24,
    routeOpacity: 1,
    routeHaloOpacity: 0.9,
};
export function getDistance(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a = Math.sin(dLat / 2) ** 2 +
        Math.cos((lat1 * Math.PI) / 180) *
            Math.cos((lat2 * Math.PI) / 180) *
            Math.sin(dLng / 2) ** 2;
    return (R *
        2 *
        Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}
export function getNearestMetro(lat, lng) {
    if (metroStations.length === 0) {
        throw new Error("Список станций метро пуст");
    }
    let nearest = metroStations[0];
    let nearestDistance = Infinity;
    for (const station of metroStations) {
        const distance = getDistance(lat, lng, station.lat, station.lng);
        if (distance < nearestDistance) {
            nearestDistance = distance;
            nearest = station;
        }
    }
    return nearest;
}
export function getWalkingTime(lat, lng, station) {
    const distance = getDistance(lat, lng, station.lat, station.lng);
    // 4.8 км/ч — чуть реалистичнее, чем ровно 5 км/ч:
    // учитывает переходы, светофоры и вход в метро.
    return Math.max(1, Math.ceil((distance / 4.8) * 60));
}
function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}
function estimateRideMinutes(from, to) {
    const distance = getDistance(from.lat, from.lng, to.lat, to.lng);
    /*
     * Средняя скорость между станциями + время стоянки.
     * Это не расписание поездов, но такая оценка заметно лучше,
     * чем старый вес "1 за любую станцию".
     */
    return clamp((distance / 42) * 60 + 0.7, 1.35, 5.5);
}
function estimateSameNameTransferMinutes(from, to) {
    const distanceMeters = getDistance(from.lat, from.lng, to.lat, to.lng) * 1000;
    /*
     * Пересадки на МЦК часто требуют выхода в наземный переход.
     * Для метро-метро используем меньший базовый штраф.
     */
    const involvesMcc = from.lineId === "mkc" ||
        to.lineId === "mkc";
    if (involvesMcc) {
        return clamp(4.5 + distanceMeters / 90, 4.5, 10);
    }
    return clamp(2.5 + distanceMeters / 120, 2.5, 7);
}
function addEdge(graph, from, edge) {
    const edges = graph.get(from);
    if (!edges) {
        return;
    }
    const existingIndex = edges.findIndex((candidate) => candidate.to === edge.to &&
        candidate.kind === edge.kind &&
        candidate.lineId === edge.lineId);
    if (existingIndex === -1) {
        edges.push(edge);
        return;
    }
    if (edge.minutes <
        edges[existingIndex].minutes) {
        edges[existingIndex] = edge;
    }
}
function addBidirectionalTransfer(graph, from, to, minutes) {
    addEdge(graph, from.id, {
        to: to.id,
        kind: "transfer",
        minutes,
    });
    addEdge(graph, to.id, {
        to: from.id,
        kind: "transfer",
        minutes,
    });
}
function buildGraph() {
    const graph = new Map();
    for (const station of metroStations) {
        graph.set(station.id, []);
    }
    /*
     * 1. Поездки внутри каждой линии.
     *
     * Узел графа = "линия + станция".
     * Поэтому одинаковые названия разных линий больше
     * не схлопываются в одну бесплатную станцию.
     */
    for (const line of metroLines) {
        for (const path of getMetroLinePaths(line)) {
            for (let index = 0; index < path.length - 1; index++) {
                const current = getLineStation(line.id, path[index][0]);
                const next = getLineStation(line.id, path[index + 1][0]);
                if (!current || !next) {
                    continue;
                }
                const minutes = estimateRideMinutes(current, next);
                const forward = {
                    to: next.id,
                    kind: "ride",
                    minutes,
                    lineId: line.id,
                    lineName: line.name,
                    lineNumber: line.number,
                    color: line.color,
                };
                const backward = {
                    ...forward,
                    to: current.id,
                };
                addEdge(graph, current.id, forward);
                addEdge(graph, next.id, backward);
            }
        }
    }
    /*
     * 2. Автоматические пересадки между одноимёнными станциями.
     */
    const byName = new Map();
    for (const station of metroStations) {
        const group = byName.get(station.name) ?? [];
        group.push(station);
        byName.set(station.name, group);
    }
    for (const [name, platforms] of byName.entries()) {
        if (platforms.length < 2 ||
            sameNameTransferExclusions.has(name)) {
            continue;
        }
        for (let i = 0; i < platforms.length; i++) {
            for (let j = i + 1; j < platforms.length; j++) {
                const from = platforms[i];
                const to = platforms[j];
                addBidirectionalTransfer(graph, from, to, estimateSameNameTransferMinutes(from, to));
            }
        }
    }
    /*
     * 3. Пересадки между станциями с разными названиями:
     * Охотный Ряд — Театральная — Площадь Революции,
     * Лубянка — Кузнецкий Мост и т.д.
     */
    for (const transfer of metroTransferGroups) {
        const platforms = transfer.members
            .map((member) => getLineStation(member.lineId, member.station))
            .filter((station) => station !== undefined);
        for (let i = 0; i < platforms.length; i++) {
            for (let j = i + 1; j < platforms.length; j++) {
                addBidirectionalTransfer(graph, platforms[i], platforms[j], transfer.minutes);
            }
        }
    }
    return graph;
}
const graph = buildGraph();
function resolveStationCandidates(station) {
    /*
     * Новый формат: id уже уникален по платформе.
     */
    const exact = metroStationById.get(station.id);
    if (exact) {
        return [exact];
    }
    /*
     * На случай объекта из старого кода:
     * пробуем восстановить платформу по lineId + name.
     */
    const stationWithOptionalLine = station;
    if (stationWithOptionalLine.lineId) {
        const byLine = metroStationById.get(stationNodeId(stationWithOptionalLine.lineId, station.name));
        if (byLine) {
            return [byLine];
        }
    }
    /*
     * Последняя совместимость со старым объектом:
     * если известна только строка name, рассматриваем
     * все одноимённые платформы как возможную точку старта/финиша.
     */
    return metroStations.filter((candidate) => candidate.name === station.name);
}
function routeSearchCost(edge) {
    /*
     * Плюс небольшой "штраф неудобства" за пересадку.
     * Он не входит в durationMinutes, а только помогает
     * не выбирать маршрут с лишней пересадкой ради экономии 20 секунд.
     */
    const transferPenalty = edge.kind === "transfer" ? 1.75 : 0;
    return edge.minutes + transferPenalty;
}
function buildRouteFromPath(routeIds, routeEdges) {
    const stations = routeIds
        .map((id) => metroStationById.get(id))
        .filter((station) => station !== undefined);
    if (stations.length !== routeIds.length) {
        return null;
    }
    const segments = [];
    const transfers = [];
    let currentSegment = null;
    let totalMinutes = 0;
    for (let index = 0; index < routeEdges.length; index++) {
        const edge = routeEdges[index];
        const from = stations[index];
        const to = stations[index + 1];
        totalMinutes += edge.minutes;
        if (edge.kind === "transfer") {
            if (currentSegment) {
                segments.push(currentSegment);
                currentSegment = null;
            }
            transfers.push({
                from,
                to,
                minutes: edge.minutes,
            });
            continue;
        }
        if (!edge.lineId ||
            !edge.lineName ||
            !edge.lineNumber ||
            !edge.color) {
            continue;
        }
        if (currentSegment &&
            currentSegment.lineId ===
                edge.lineId) {
            currentSegment.stations.push(to);
            currentSegment.minutes +=
                edge.minutes;
            continue;
        }
        if (currentSegment) {
            segments.push(currentSegment);
        }
        currentSegment = {
            lineId: edge.lineId,
            line: edge.lineName,
            lineNumber: edge.lineNumber,
            color: edge.color,
            stations: [from, to],
            minutes: edge.minutes,
        };
    }
    if (currentSegment) {
        segments.push(currentSegment);
    }
    const lines = segments.reduce((result, segment) => {
        if (result[result.length - 1] !==
            segment.line) {
            result.push(segment.line);
        }
        return result;
    }, []);
    return {
        stations,
        lines,
        segments,
        transfers,
        durationMinutes: Math.max(0, Math.round(totalMinutes)),
        transferCount: transfers.length,
    };
}
export function findMetroRoute(start, end) {
    const startCandidates = resolveStationCandidates(start);
    const endCandidates = resolveStationCandidates(end);
    if (startCandidates.length === 0 ||
        endCandidates.length === 0) {
        return null;
    }
    const endIds = new Set(endCandidates.map((station) => station.id));
    const distances = new Map();
    const previous = new Map();
    const visited = new Set();
    for (const station of metroStations) {
        distances.set(station.id, Infinity);
        previous.set(station.id, null);
    }
    for (const candidate of startCandidates) {
        distances.set(candidate.id, 0);
    }
    let reachedEnd = null;
    /*
     * При текущем размере Московского метро сортировка массива
     * достаточно быстра. Если сеть заметно вырастет, сюда легко
     * заменить очередь на binary heap, не меняя остальной код.
     */
    const queue = startCandidates.map((station) => station.id);
    while (queue.length > 0) {
        queue.sort((a, b) => (distances.get(a) ?? Infinity) -
            (distances.get(b) ?? Infinity));
        const current = queue.shift();
        if (!current) {
            break;
        }
        if (visited.has(current)) {
            continue;
        }
        visited.add(current);
        if (endIds.has(current)) {
            reachedEnd = current;
            break;
        }
        for (const edge of graph.get(current) ?? []) {
            if (visited.has(edge.to)) {
                continue;
            }
            const candidateDistance = (distances.get(current) ??
                Infinity) +
                routeSearchCost(edge);
            if (candidateDistance <
                (distances.get(edge.to) ??
                    Infinity)) {
                distances.set(edge.to, candidateDistance);
                previous.set(edge.to, {
                    from: current,
                    edge,
                });
                queue.push(edge.to);
            }
        }
    }
    if (!reachedEnd) {
        return null;
    }
    const routeIds = [];
    const routeEdges = [];
    let current = reachedEnd;
    while (current !== null) {
        routeIds.unshift(current);
        const step = previous.get(current) ?? null;
        if (!step) {
            break;
        }
        routeEdges.unshift(step.edge);
        current = step.from;
    }
    return buildRouteFromPath(routeIds, routeEdges);
}
/**
 * Для renderer'а карты.
 * Вместо одной ломаной всего маршрута рисуйте каждый segment отдельно:
 *
 * route.segments.map(segment => (
 *   <Polyline
 *     positions={segment.stations.map(s => [s.lat, s.lng])}
 *     pathOptions={{ color: segment.color }}
 *   />
 * ))
 */
export function getRouteRenderSegments(route) {
    return route.segments.map((segment) => ({
        lineId: segment.lineId,
        line: segment.line,
        lineNumber: segment.lineNumber,
        color: segment.color,
        positions: segment.stations.map((station) => [
            station.lat,
            station.lng,
        ]),
    }));
}
export function getMetroLineRenderPaths() {
    return metroLines.flatMap((line) => getMetroLinePaths(line).map((path) => ({
        lineId: line.id,
        line: line.name,
        lineNumber: line.number,
        color: line.color,
        render: line.render ?? "solid",
        positions: path.map(([, lat, lng]) => [lat, lng]),
    })));
}
export function getLineColor(lineId) {
    return (metroLineById.get(lineId)?.color ??
        "#6B7280");
}
