export const invokeRequest = async (targetUrl, requestInit, readableBody)=>{
    const invokeHeaders = {
        "cache-control": "",
        ...requestInit.headers
    };
    return await fetch(targetUrl, {
        headers: invokeHeaders,
        method: requestInit.method,
        redirect: "manual",
        signal: requestInit.signal,
        ...requestInit.method !== "GET" && requestInit.method !== "HEAD" && readableBody ? {
            body: readableBody,
            duplex: "half"
        } : {},
        next: {
            // @ts-ignore
            internal: true
        }
    });
};

//# sourceMappingURL=invoke-request.js.map