// site/src/lib/alignByDate.ts

type Row = { date: string; [key: string]: any };

export function alignByIntersection<
  E extends Row,
  A extends Row,
  R extends Row
>(exposures: E[], attribution: A[], regimes: R[]) {
  const Sexp = new Set(exposures.map(d => d.date));
  const Satt = new Set(attribution.map(d => d.date));
  const Sreg = new Set(regimes.map(d => d.date));

  const commonDates = [...Sexp]
    .filter(d => Satt.has(d) && Sreg.has(d))
    .sort();

  const commonSet = new Set(commonDates);

  const expAligned = exposures.filter(r => commonSet.has(r.date));
  const attAligned = attribution.filter(r => commonSet.has(r.date));
  const regAligned = regimes.filter(r => commonSet.has(r.date));

  return {
    dates: commonDates,
    exposures: expAligned,
    attribution: attAligned,
    regimes: regAligned,
    dropped: {
      exposures: exposures.length - expAligned.length,
      attribution: attribution.length - attAligned.length,
      regimes: regimes.length - regAligned.length,
    },
  };
}
