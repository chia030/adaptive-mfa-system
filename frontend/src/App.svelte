<script>
	import Login from './Login.svelte';
	import MFASelection from './MFASelection.svelte';
	import OTPVerification from './OTPVerification.svelte';

	//TODO: add logout
	
	let isAuthenticated = false;
	let isMfaRequired = false;
	let isMfaPassed = false;
	let thisAvailableMFAMethods = [];
	
	let accessToken = "";
  	let userEmail = "";
	let fingerprint = "";
	
	// login process
	function handleLogin(event) {
		event.preventDefault();
		const { username, password, device_id, authenticated, mfaRequired, mfaPassed, availableMFAMethods, token } = event.detail;
		userEmail = username;
		fingerprint = device_id;
		isAuthenticated = authenticated;
		isMfaRequired = mfaRequired;
		isMfaPassed = mfaPassed;
		accessToken = token;
		thisAvailableMFAMethods = availableMFAMethods || [ { id: 'email', name: 'Email OTP' } ];
	}
	
	// simulate MFA selection handling
	function handleSelectMethod(event) {
		console.log("MFA method selected:", event.detail);
	}

	async function handleMfaVerification({detail: otp}) {
		try {
			// POST to backend Auth Service API
			const response = await fetch('http://localhost:8000/auth/verify-otp', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					email: userEmail,
					device_id: fingerprint,
					otp: otp
				})
			});
			const data = await response.json();
			if (response.ok) {
				isMfaPassed = true;
				token = data.access_token;
			} else {
				console.error('OTP verification failed:', data.detail);
			}
		} catch (error) {
			console.error('Error during OTP verification:', error);
		}
	}
</script>

<main>
	{#if !isAuthenticated}
	<Login on:login={(event) => handleLogin(event)}/>
	{:else if isMfaRequired && !isMfaPassed}
		<!-- MFASelection for choosing a method -->
		<MFASelection methods={thisAvailableMFAMethods} on:select={handleSelectMethod}/>
		<!-- OTPVerification for entering the received OTP -->
		<OTPVerification on:verify={handleMfaVerification} />
	{:else if !isMfaRequired || isMfaPassed }
		<h2>Welcome, you are now securely authenticated!</h2>
		 <p>Token: {accessToken}</p>
	{/if} 
</main>

<style>
	main {
		text-align: center;
		padding: 1em;
		max-width: 240px;
		margin: 0 auto;
	}

	h1 {
		color: #ff3e00;
		text-transform: uppercase;
		font-size: 4em;
		font-weight: 100;
	}

	@media (min-width: 640px) {
		main {
			max-width: none;
		}
	}
</style>
