//VERSION=3
function setup() {
  return {
    input: ["VV", "VH", "dataMask"],
    output: [{
      id: "VV",
      bands: 1,
      sampleType: "FLOAT32"
    }, {
      id: "VH",
      bands: 1,
      sampleType: "FLOAT32"
    }, {
      id: "MASK",
      bands: 1,
      sampleType: "UINT8"
    }]
  };
}

function evaluatePixel(samples) {
  return {
    VV: [samples.VV],
    VH: [samples.VH],
    MASK: [samples.dataMask]
  };
}