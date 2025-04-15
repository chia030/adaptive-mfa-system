<!-- src/Login.svelte -->
<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import FingerprintJS from '@fingerprintjs/fingerprintjs';

  const dispatch = createEventDispatcher();
  
  let username = "";
  let password = "";
  let fingerprint = '';

  let errorMessage = '';
  let successMessage = '';

  let authenticated = false;
	let mfaRequired = false;
	let availableMFAMethods = [];

  // generate device fingerprint at mount
  onMount(async () => {
    try {
      // load FingerprintJS agent
      const fpPromise = FingerprintJS.load();
      const fp = await fpPromise;
      const result = await fp.get();
      fingerprint = result.visitorId;
      console.log('Device Fingerprint:', fingerprint);
    } catch (error) {
      console.error('Error generating fingerprint:', err);
      errorMessage = 'Could not generate device fingerprint.';
    }
  });
  
  async function handleSubmit(event) {
    event.preventDefault();

    // payload matching OAuth2PasswordRequestForm
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('device_id', fingerprint);

    try {
      // POST to backend API
      const response = await fetch('http://localhost:8000/better-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      });

      const data = await response.json();
      if (response.ok) {
        // check if MFA required
        if (data.message && data.message.includes("MFA required")) {
          authenticated = true;
          mfaRequired = true;
          availableMFAMethods = data.availableMFAMethods || [
            { id: 'sms', name: 'SMS OTP' },
            { id: 'email', name: 'Email OTP' }
          ];
          
        } else {
          // MFA not required
          authenticated = true;
          mfaRequired = false;
          // save token
          successMessage = 'Login successful! Token: ' + data.access_token;
          errorMessage = '';
        }
      } else {
        errorMessage = data.detail || "Login failed.";
      }
    } catch (error) {
      console.error(error);
      errorMessage = 'A network error occurred.';
    };
    // Dispatch a login event with credentials
    dispatch('login', { username, password, device_id: fingerprint, authenticated, mfaRequired, availableMFAMethods });
  }
</script>

<style>
  /* Basic styling for the login form */
  .login-container {
    max-width: 400px;
    margin: 3rem auto;
    padding: 2rem;
    border-radius: 8px;
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
  input, button {
    width: 100%;
    padding: 0.75rem;
    margin: 0.5rem 0;
    border-radius: 4px;
    border: 1px solid #ccc;
  }
  button {
    background-color: #007BFF;
    color: #fff;
    border: none;
    cursor: pointer;
  }
  button:hover {
    background-color: #0056b3;
  }
  .message {
    margin-top: 1rem;
    font-size: 0.9rem;
  }
  .error {
    color: red;
  }
  .success {
    color: green;
  }
</style>

<div class="login-container">
  <h2>Login</h2>
  <form on:submit={handleSubmit}>
    <input
      id="username"
      type="email"
      name="email"
      bind:value={username}
      placeholder="Email"
      required
    />
    <input
      id="password"
      type="password"
      name="password"
      bind:value={password}
      placeholder="Password"
      required
    />
    <button type="submit">Login</button>
  </form>
  {#if errorMessage}
    <div class="message error">{errorMessage}</div>
  {/if}
  {#if successMessage}
    <div class="message success">{successMessage}</div>
  {/if}
</div>

<!-- <form on:submit={handleSubmit}>
  <div>
    <label for="username">Email:</label>
    <input id="username" type="text" bind:value={username} required />
  </div>
  <div>
    <label for="password">Password:</label>
    <input id="password" type="password" bind:value={password} required />
  </div>
  <button type="submit">Login</button>
</form> -->
